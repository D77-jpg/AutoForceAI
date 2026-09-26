import os
import requests
import uuid
import json  # Added json import
import random # Added random
import string # Added string
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db_manager import get_shared_db
from database.shared_models import User, Organization, UserRole
from core.auth import create_access_token, get_password_hash, is_production, verify_password
from core.login_security import failed_login_policy, validate_registration_password
from core.dependencies import get_current_user_id


router = APIRouter(prefix="/auth", tags=["Authentication"])

# --- Config ---
WECHAT_APP_ID = os.getenv("WECHAT_APP_ID")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET")
WECHAT_REDIRECT_URI = os.getenv("WECHAT_REDIRECT_URI")
# Whether to allow open email registration (first user always becomes system admin)
ALLOW_EMAIL_REGISTER = os.getenv("ALLOW_EMAIL_REGISTER", "true").lower() == "true"

# --- Schemas ---
class WeChatLoginRequest(BaseModel):
    code: str

class EmailRegisterRequest(BaseModel):
    email: str
    password: str
    nickname: Optional[str] = None

class EmailLoginRequest(BaseModel):
    email: str
    password: str

class OrganizationCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None

class OrganizationJoinRequest(BaseModel):
    name: str  # Check name
    invite_code: str # Check code

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    role: str
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    invite_code: Optional[str] = None # Added invite code for admins

# --- Endpoints ---

def _build_login_response(user: User, db: Session) -> dict:
    """Shared response builder for all login/register paths."""
    org_name = user.organization.name if user.organization else None
    role_str = user.role.value if hasattr(user.role, 'value') else user.role
    invite_code = None
    if user.organization and role_str == UserRole.ENTERPRISE_ADMIN.value:
        invite_code = user.organization.invite_code

    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "role": role_str,
            "org_id": user.organization_id,
            "nickname": user.nickname,
            "avatar": user.avatar,
        }
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "role": role_str,
        "organization_id": user.organization_id,
        "organization_name": org_name,
        "invite_code": invite_code,
    }


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def email_register(request: EmailRegisterRequest, db: Session = Depends(get_shared_db)):
    """
    Email + password registration (formal account system).
    The very first user in the system becomes the system admin.
    """
    if not ALLOW_EMAIL_REGISTER:
        raise HTTPException(status_code=403, detail="邮箱注册未开放，请联系管理员开通账号")

    email = request.email.strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    validate_registration_password(request.password)

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")

    # First user becomes system admin
    user_count = db.query(User).count()
    role = UserRole.ADMIN if user_count == 0 else UserRole.USER

    user = User(
        username=f"e_{uuid.uuid4().hex[:12]}",  # clean ASCII system username
        nickname=request.nickname or email.split("@")[0],
        email=email,
        hashed_password=get_password_hash(request.password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _build_login_response(user, db)


@router.post("/login", response_model=LoginResponse)
def email_login(request: EmailLoginRequest, http_request: Request, db: Session = Depends(get_shared_db)):
    """Email + password login with a per-account/client failed-attempt cooldown."""
    email = request.email.strip().lower()
    client_ip = http_request.client.host if http_request.client else "unknown"
    failed_login_policy.check(email, client_ip)
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.hashed_password or not verify_password(request.password, user.hashed_password):
        failed_login_policy.fail(email, client_ip)
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被停用，请联系管理员")
    failed_login_policy.success(email, client_ip)
    return _build_login_response(user, db)


@router.post("/organization/create", response_model=LoginResponse)
def create_organization(
    request: OrganizationCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    # Check current user
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.organization_id:
        raise HTTPException(status_code=400, detail="You are already in an organization")
        
    # Check org name
    existing = db.query(Organization).filter(Organization.name == request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization name already exists")
    
    # Generate Invite Code
    import random, string
    invite_code = ''.join(random.choices(string.digits, k=6))
    
    # Create Org
    new_org = Organization(
        name=request.name,
        description=request.description,
        invite_code=invite_code
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    
    # Assign User
    user.organization_id = new_org.id
    user.role = UserRole.ENTERPRISE_ADMIN.value
    db.commit()
    
    # Return updated user info (LoginResponse style)
    return {
        "access_token": "valid_session", # Frontend should keeping using current token
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "role": user.role,
        "organization_id": new_org.id,
        "organization_name": new_org.name,
        "invite_code": new_org.invite_code
    }

@router.get("/me", response_model=LoginResponse)
def get_current_user_info(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    org = None
    if user.organization_id:
        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        
    return {
        "access_token": "valid_session", # Mock token just to satisfy schema
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": org.name if org else None,
        "avatar": user.avatar,
        "invite_code": org.invite_code if org and user.role == UserRole.ENTERPRISE_ADMIN.value else None
    }

@router.post("/organization/join", response_model=LoginResponse)
def join_organization(
    request: OrganizationJoinRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.organization_id is not None:
        raise HTTPException(status_code=400, detail="User already in an organization")

    org = db.query(Organization).filter(Organization.name == request.name).first()
    if not org:
        raise HTTPException(status_code=404, detail="该组织不存在")
        
    if org.invite_code != request.invite_code:
        raise HTTPException(status_code=403, detail="无效的邀请码")
        
    user.organization_id = org.id
    user.role = UserRole.USER.value
    db.commit()
    
    return {
        "access_token": "valid_session",
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "role": user.role,
        "organization_id": org.id,
        "organization_name": org.name,
        "avatar": user.avatar
    }

@router.get("/wechat/url")
def get_wechat_auth_url():
    """Generates the WeChat QR connect URL"""
    if not WECHAT_APP_ID or "wx" not in WECHAT_APP_ID or not WECHAT_APP_SECRET or not WECHAT_REDIRECT_URI:
        if is_production():
            raise HTTPException(status_code=503, detail="微信登录未配置")
        return {"url": "#", "mock_mode": True, "msg": "WECHAT_APP_ID not configured"}
    
    base_url = "https://open.weixin.qq.com/connect/qrconnect"
    # scope=snsapi_login is for PC Website QR Code
    import urllib.parse
    encoded_redirect_uri = urllib.parse.quote(WECHAT_REDIRECT_URI)
    url = f"{base_url}?appid={WECHAT_APP_ID}&redirect_uri={encoded_redirect_uri}&response_type=code&scope=snsapi_login&state=STATE#wechat_redirect"
    return {"url": url, "mock_mode": False}

@router.post("/wechat/login", response_model=LoginResponse)
def wechat_login(request: WeChatLoginRequest, db: Session = Depends(get_shared_db)):
    """
    Exchanges WeChat Code for JWT Token.
    Supports both Real API (if env configured) and Mock (if code startswith 'mock_').
    """
    
    openid = None
    unionid = None
    nickname = None
    avatar_url = None

    # Production must reject mock codes and missing configuration before DB access.
    mock_code = request.code.startswith("mock_")
    configured = bool(WECHAT_APP_ID and "wx" in WECHAT_APP_ID and WECHAT_APP_SECRET and WECHAT_REDIRECT_URI)
    if is_production() and (mock_code or not configured):
        raise HTTPException(status_code=403 if mock_code else 503, detail="微信登录不可用")
    is_mock = mock_code or not configured

    if is_mock:
        openid = f"gh_{request.code}"
        nickname = f"User_{request.code[-4:]}"
    else:
        # Real WeChat API Exchange
        token_url = f"https://api.weixin.qq.com/sns/oauth2/access_token?appid={WECHAT_APP_ID}&secret={WECHAT_APP_SECRET}&code={request.code}&grant_type=authorization_code"
        try:
            resp = requests.get(token_url, timeout=10).json()
            if "errcode" in resp:
                raise HTTPException(status_code=400, detail="微信授权失败")
            
            openid = resp["openid"]
            unionid = resp.get("unionid") 
            access_token_wx = resp["access_token"]
            
            # Optional: Get User Info
            user_info_url = f"https://api.weixin.qq.com/sns/userinfo?access_token={access_token_wx}&openid={openid}"
            user_info_resp = requests.get(user_info_url, timeout=10)
            # FORCE UTF-8 DECODING (Fixes encoding issues with WeChat API)
            try:
                content = user_info_resp.content
                # Try decoding as utf-8, fallback to latin-1 if needed, but usually utf-8 is correct for WeChat JSON
                decoded_content = content.decode('utf-8')
                user_info = json.loads(decoded_content)
            except (ValueError, UnicodeError):
                user_info = user_info_resp.json() # Fallback
            
            nickname = user_info.get("nickname", f"User_{openid[:4]}")
            
            # Fix Avatar URL Scheme (http -> https)
            avatar_url = user_info.get("headimgurl")
            if avatar_url and avatar_url.startswith("http://"):
                avatar_url = avatar_url.replace("http://", "https://")
            
        except HTTPException:
            raise
        except (requests.RequestException, ValueError, KeyError, UnicodeError):
            raise HTTPException(status_code=502, detail="微信服务暂不可用")

    # 2. Find or Create User
    # Try finding by unionid first (if enterprise has multiple apps), then openid
    user = None
    if unionid:
        user = db.query(User).filter(User.wechat_unionid == unionid).first()
    
    if not user:
        user = db.query(User).filter(User.wechat_openid == openid).first()

    is_new = False
    if user and not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被停用，请联系管理员")

    if not user:
        is_new = True
        # Check if first user in system -> System Admin
        user_count = db.query(User).count()
        role = UserRole.ADMIN if user_count == 0 else UserRole.USER
        
        # [SECURITY FIX] Generate clean, ASCII-only system username
        # Do NOT use nickname for username to avoid encoding/garbled issues
        sys_username = f"u_{uuid.uuid4().hex[:12]}"
        
        user = User(
            username=sys_username,
            nickname=nickname, # Explicitly set nickname (Display Name)
            avatar=avatar_url, # Explicitly set avatar
            wechat_openid=openid,
            wechat_unionid=unionid,
            role=role,
            is_active=True
        )
        db.add(user)
    
    # 2.5 Update Profile (Always update with latest WeChat info on login)
    # This solves the issue for existing users too
    # Logic Update: Only overwrite avatar if it's NOT a custom uploaded one (which starts with /uploads or similar local path)
    # OR if the user doesn't have an avatar yet.
    # We assume WeChat avatars are full URLs (http/https). Local uploads are /uploads/... or http://domain/uploads/...
    
    # Update nickname if it came from WeChat (optional, maybe user wants to keep custom nickname? 
    # For now, let's prioritize WeChat nickname if it's available, OR keep existing if we want. 
    # Current behavior was: user.nickname = nickname. 
    # Let's change behavior: Only set if user.nickname is empty or default format? 
    # User asked about AVATAR specifically. Let's fix AVATAR first.
    
    if avatar_url:
        # Check if current avatar is a custom upload (we use a simple heuristic: contains '/uploads/')
        is_custom_avatar = user.avatar and "/uploads/" in user.avatar
        if not is_custom_avatar:
             user.avatar = avatar_url

    # For Nickname: Only update if the user has no nickname yet. 
    # We do NOT want to overwrite a user's custom nickname with the WeChat nickname on every login.
    if not user.nickname:
        user.nickname = nickname
    
    # If using existing user but nickname/avatar changed, we commit updates
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="无法保存用户信息")

    # Do not log profile data or upstream credentials, even in debug mode.

    # 3. Create Access Token (Include Role and Org in claim if possible, or just user_id)
    # We put role/org in token for frontend convenience, but verify_token usually just checks userId
    access_token = create_access_token(
        data={
            "sub": user.username, 
            "user_id": user.id,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "org_id": user.organization_id,
            "nickname": nickname, # Store in token for easy access
            "avatar": avatar_url
        }
    )

    org_name = user.organization.name if user.organization else None
    
    # Handle enum serialization for response
    role_str = user.role.value if hasattr(user.role, 'value') else user.role
    
    # Logic to get invite code safely
    invite_code = None
    if user.organization and role_str == UserRole.ENTERPRISE_ADMIN.value:
         invite_code = user.organization.invite_code

    # Use local variables 'nickname' and 'avatar_url' for response to ensure immediate feedback
    # regardless of DB persistence state (e.g. if DB migration hasn't applied yet)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "nickname": nickname or user.nickname, 
        "avatar": avatar_url or user.avatar,    
        "role": role_str,
        "organization_id": user.organization_id,
        "organization_name": org_name,
        "invite_code": invite_code
    }

@router.post("/organization", status_code=status.HTTP_201_CREATED)
def create_organization(
    request: OrganizationCreateRequest, 
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    """Create a new Organization and properly assign the Creator as Enterprise Admin."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.organization_id:
        raise HTTPException(status_code=400, detail="User already belongs to an organization")

    # Create Org
    new_org = Organization(
        name=request.name,
        description=request.description
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)

    # Update User
    user.organization_id = new_org.id
    user.role = UserRole.ENTERPRISE_ADMIN
    db.commit()

    return {"msg": "Organization created", "organization_id": new_org.id, "role": user.role}

@router.post("/organization/join")
def join_organization(
    request: OrganizationJoinRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    """User joins an existing organization."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.organization_id:
        raise HTTPException(status_code=400, detail="User already belongs to an organization")

    org = db.query(Organization).filter(Organization.id == request.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="该组织不存在")
    
    user.organization_id = org.id
    # Default role stays USER
    db.commit()

    return {"msg": f"Joined organization {org.name}", "organization_id": org.id}

class UserProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None # Will serve as Signature
    avatar: Optional[str] = None

@router.get("/me")
def get_current_user_profile(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname, # Added
        "avatar": user.avatar,     # Added
        "email": user.email,
        "phone": user.phone,
        "bio": user.bio,
        "role": user.role,
        "is_wechat_bound": bool(user.wechat_openid or user.wechat_unionid),
        "organization_id": user.organization_id,
        "organization_name": user.organization.name if user.organization else None,
        "created_at": user.created_at
    }

@router.patch("/profile")
def update_user_profile(
    profile: UserProfileUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if profile.nickname is not None:
        user.nickname = profile.nickname
    if profile.email is not None:
        user.email = profile.email
    if profile.phone is not None:
        user.phone = profile.phone
    if profile.bio is not None:
        user.bio = profile.bio
    if profile.avatar is not None:
        user.avatar = profile.avatar
        
    db.commit()
    db.refresh(user)
    
    return {
        "msg": "Profile updated successfully",
        "user": {
            "nickname": user.nickname,
            "email": user.email,
            "phone": user.phone,
            "bio": user.bio,
            "avatar": user.avatar
        }
    }

@router.get("/organization/list")
def list_organizations(db: Session = Depends(get_shared_db)):
    """List all organizations (for now, public/internal use to let users pick)."""
    orgs = db.query(Organization).all()
    return [{"id": o.id, "name": o.name, "description": o.description} for o in orgs]

