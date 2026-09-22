from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from core.db_manager import get_shared_db
from database.shared_models import User, Organization, UserRole
from core.dependencies import get_current_user_id

router = APIRouter(prefix="/api/v1/admin", tags=["System Administration"])

# --- Schemas ---

class UserSchema(BaseModel):
    id: int
    username: Optional[str] = None
    nickname: Optional[str] = None
    email: Optional[str] = None
    role: str
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    created_at: datetime
    is_active: bool

    class Config:
        orm_mode = True

class OrganizationSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    user_count: int = 0
    admin_username: Optional[str] = None
    invite_code: Optional[str] = None

    class Config:
        orm_mode = True

class OrganizationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    admin_email: Optional[str] = None # Optional: invite admin by email

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class SetOrgAdminRequest(BaseModel):
    user_id: int

class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None  # admin / enterprise_admin / user
    is_active: Optional[bool] = None

# --- Endpoints ---

@router.get("/users", response_model=List[UserSchema])
def list_users(
    skip: int = 0, 
    limit: int = 100, 
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    current_user = db.query(User).filter(User.id == current_user_id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")

    query = db.query(User)
    
    # Role Based Access Control
    if current_user.role == UserRole.ENTERPRISE_ADMIN.value:
        # Enterprise Admin: Only see users in same organization
        if not current_user.organization_id:
            return [] # Should not happen for an enterprise admin
        query = query.filter(User.organization_id == current_user.organization_id)
    elif current_user.role == UserRole.ADMIN.value:
        # System Admin: See all users
        pass
    else:
        # Regular User: Only see self (or forbidden?)
        # For safety, let's restrict to self or empty list if they try to list all
        # Or better yet, maybe return 403. But let's stick to "data isolation" principle first.
        # We'll allow them to see themselves, which is useful for debugging.
        query = query.filter(User.id == current_user.id)

    users = query.offset(skip).limit(limit).all()
    result = []
    for u in users:
        org_name = None
        # Manually check relationship (optional) or rely on lazy loading if configured
        try:
             # The relationship "organization" might not be eager loaded. 
             # Safe access if relationship is defined in SQLA models:
             if u.organization:
                 org_name = u.organization.name
        except:
             pass 

        result.append({
            "id": u.id,
            "username": u.username,
            "nickname": u.nickname,
            "email": u.email,
            "role": u.role,
            "organization_id": u.organization_id,
            "organization_name": org_name,
            "created_at": u.created_at,
            "is_active": True # Default to true for now
        })
    return result

@router.get("/users/{user_id}", response_model=UserSchema)
def get_user(
    user_id: int, 
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    current_user = db.query(User).filter(User.id == current_user_id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Permission Check
    if current_user.role == UserRole.ENTERPRISE_ADMIN.value:
        if user.organization_id != current_user.organization_id:
             raise HTTPException(status_code=403, detail="Access denied: Different Organization")
    elif current_user.role == UserRole.ADMIN.value:
        pass
    else:
        if user.id != current_user.id:
             raise HTTPException(status_code=403, detail="Access denied")
    
    org_name = user.organization.name if user.organization else None
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": org_name,
        "created_at": user.created_at,
        "is_active": user.is_active or True
    }

@router.patch("/users/{user_id}", response_model=UserSchema)
def update_user(
    user_id: int,
    updates: UserUpdateRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    """Admin: update a user's profile / role / active status."""
    current_user = db.query(User).filter(User.id == current_user_id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Permission: system admin can edit anyone; enterprise admin only within own org
    if current_user.role == UserRole.ADMIN.value:
        pass
    elif current_user.role == UserRole.ENTERPRISE_ADMIN.value:
        if user.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Access denied: Different Organization")
        # Enterprise admin cannot promote to system admin or edit system admins
        if updates.role == UserRole.ADMIN.value or user.role == UserRole.ADMIN.value:
            raise HTTPException(status_code=403, detail="Insufficient permission")
    else:
        raise HTTPException(status_code=403, detail="Admin permission required")

    # Self-protection: cannot deactivate / demote yourself
    if user.id == current_user.id:
        if updates.is_active is False:
            raise HTTPException(status_code=400, detail="不能停用自己的账号")
        if updates.role and updates.role != user.role:
            raise HTTPException(status_code=400, detail="不能修改自己的角色")

    # Role validation
    valid_roles = {r.value for r in UserRole}
    if updates.role is not None and updates.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"非法角色: {updates.role}")

    # Email uniqueness
    if updates.email is not None and updates.email != user.email:
        email = updates.email.strip().lower()
        if email:
            conflict = db.query(User).filter(User.email == email, User.id != user_id).first()
            if conflict:
                raise HTTPException(status_code=409, detail="该邮箱已被其他账号使用")
            user.email = email

    if updates.nickname is not None:
        user.nickname = updates.nickname
    if updates.role is not None:
        user.role = updates.role
    if updates.is_active is not None:
        user.is_active = updates.is_active

    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": user.organization.name if user.organization else None,
        "created_at": user.created_at,
        "is_active": user.is_active
    }

@router.get("/organizations", response_model=List[OrganizationSchema])
def list_organizations(
    skip: int = 0, 
    limit: int = 100, 
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    current_user = db.query(User).filter(User.id == current_user_id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")

    query = db.query(Organization)
    
    # Role Based Access Control
    if current_user.role == UserRole.ENTERPRISE_ADMIN.value:
        # Enterprise Admin: Only see their own organization
        if not current_user.organization_id:
            return []
        query = query.filter(Organization.id == current_user.organization_id)
    elif current_user.role == UserRole.ADMIN.value:
        # System Admin: See all organizations
        pass
    else:
        # Regular User: Only see their own org
        if current_user.organization_id:
             query = query.filter(Organization.id == current_user.organization_id)
        else:
             return []

    orgs = query.offset(skip).limit(limit).all()
    result = []
    for o in orgs:
        # Count users
        user_count = db.query(User).filter(User.organization_id == o.id).count()
        # Find admin (first enterprise_admin)
        admin = db.query(User).filter(User.organization_id == o.id, User.role == UserRole.ENTERPRISE_ADMIN.value).first()
        
        result.append({
            "id": o.id,
            "name": o.name,
            "description": o.description,
            "created_at": o.created_at,
            "user_count": user_count,
            "admin_username": admin.nickname if admin else None,
            "invite_code": o.invite_code
        })
    return result

@router.post("/organizations", response_model=OrganizationSchema)
def create_organization(
    org_in: OrganizationCreate,
    db: Session = Depends(get_shared_db)
):
    # Check if name exists
    existing = db.query(Organization).filter(Organization.name == org_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization name already exists")
    
    # Generate Invite Code
    import random, string
    invite_code = ''.join(random.choices(string.digits, k=6))
    
    new_org = Organization(
        name=org_in.name,
        description=org_in.description,
        invite_code=invite_code
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    
    return {
        "id": new_org.id,
        "name": new_org.name,
        "description": new_org.description,
        "created_at": new_org.created_at,
        "user_count": 0,
        "admin_username": None,
        "invite_code": new_org.invite_code
    }

@router.put("/organizations/{org_id}/invite-code")
def refresh_organization_invite_code(
    org_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    current_user = db.query(User).filter(User.id == current_user_id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")
        
    # Permission Check
    if current_user.role == UserRole.ENTERPRISE_ADMIN.value:
        if current_user.organization_id != org_id:
             raise HTTPException(status_code=403, detail="Permission Denied")
    elif current_user.role == UserRole.ADMIN.value:
        pass
    else:
        raise HTTPException(status_code=403, detail="Permission Denied")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    # Generate New Invite Code
    import random, string
    invite_code = ''.join(random.choices(string.digits, k=6))
    org.invite_code = invite_code
    db.commit()
    
    return {"msg": "Invite code refreshed", "invite_code": invite_code}

@router.post("/organizations/{org_id}/admin")
def set_organization_admin(
    org_id: int,
    request: SetOrgAdminRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    current_user = db.query(User).filter(User.id == current_user_id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")
        
    if current_user.role == UserRole.ENTERPRISE_ADMIN.value:
        if current_user.organization_id != org_id:
             raise HTTPException(status_code=403, detail="Permission Denied")
    elif current_user.role == UserRole.ADMIN.value:
        pass
    else:
        raise HTTPException(status_code=403, detail="Permission Denied")
        
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Ensure target user belongs to the organization
    if user.organization_id != org_id:
         raise HTTPException(status_code=400, detail="Target user is not in this organization")
    
    # Logic: Set user to this org and upgrade role
    # 1. Downgrade existing admins of this org to normal members
    existing_admins = db.query(User).filter(
        User.organization_id == org.id,
        User.role == UserRole.ENTERPRISE_ADMIN.value
    ).all()
    
    for admin in existing_admins:
        if admin.id != user.id:
            admin.role = UserRole.USER.value # Downgrade to regular user

    # 2. Upgrade new admin
    user.organization_id = org.id
    user.role = UserRole.ENTERPRISE_ADMIN.value
    db.commit()
    
    return {"msg": f"User {user.username} is now admin of {org.name}"}

@router.patch("/organizations/{org_id}", response_model=OrganizationSchema)
def update_organization(
    org_id: int,
    org_in: OrganizationUpdate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    current_user = db.query(User).filter(User.id == current_user_id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")

    if current_user.role == UserRole.ENTERPRISE_ADMIN.value:
        if current_user.organization_id != org_id:
             raise HTTPException(status_code=403, detail="Permission Denied")
    elif current_user.role == UserRole.ADMIN.value:
        pass
    else:
        raise HTTPException(status_code=403, detail="Permission Denied")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if org_in.name:
        # Check uniqueness if name changed
        if org_in.name != org.name:
            if db.query(Organization).filter(Organization.name == org_in.name).first():
                raise HTTPException(status_code=400, detail="Organization name already exists")
        org.name = org_in.name
    
    if org_in.description is not None:
        org.description = org_in.description
        
    db.commit()
    db.refresh(org)
    
    # Re-calculate aggregates for response schema
    user_count = db.query(User).filter(User.organization_id == org.id).count()
    admin = db.query(User).filter(User.organization_id == org.id, User.role == UserRole.ENTERPRISE_ADMIN.value).first()

    return {
        "id": org.id,
        "name": org.name,
        "description": org.description,
        "created_at": org.created_at,
        "user_count": user_count,
        "admin_username": admin.nickname if admin else None,
        "invite_code": org.invite_code
    }

@router.get("/organizations/{org_id}/users", response_model=List[UserSchema])
def get_organization_users(
    org_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    current_user = db.query(User).filter(User.id == current_user_id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")

    # Authorization Check
    if current_user.role == UserRole.ENTERPRISE_ADMIN.value:
        if current_user.organization_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied to other organization data")
    elif current_user.role == UserRole.ADMIN.value:
        pass
    else:
        # Regular user? Usually shouldn't be here, but let's allow if they are in the org
        # But this is admin API. Safe to deny or allow based on org membership.
        if current_user.organization_id != org_id:
             raise HTTPException(status_code=403, detail="Access denied")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    users = db.query(User).filter(User.organization_id == org_id).offset(skip).limit(limit).all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "username": u.username,
            "nickname": u.nickname,
            "email": u.email,
            "role": u.role,
            "organization_id": u.organization_id,
            "organization_name": org.name,
            "created_at": u.created_at,
            "is_active": True
        })
    return result

@router.delete("/organizations/{org_id}/users/{user_id}")
def remove_user_from_organization(
    org_id: int,
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_shared_db)
):
    current_user = db.query(User).filter(User.id == current_user_id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")
        
    # Check permissions
    if current_user.role == UserRole.ENTERPRISE_ADMIN.value:
        if current_user.organization_id != org_id:
            raise HTTPException(status_code=403, detail="Permission Denied")
    elif current_user.role == UserRole.ADMIN.value:
        pass
    else:
        raise HTTPException(status_code=403, detail="Permission Denied")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    user_to_remove = db.query(User).filter(User.id == user_id).first()
    # Check if user is actually in that org
    if not user_to_remove or user_to_remove.organization_id != org_id:
        raise HTTPException(status_code=404, detail="User not found in this organization")

    # Reset user
    user_to_remove.organization_id = None
    # If they were admin, they lose that status
    if user_to_remove.role == UserRole.ENTERPRISE_ADMIN.value:
        user_to_remove.role = UserRole.USER.value
        
    db.commit()
    return {"msg": "User removed from organization"}
