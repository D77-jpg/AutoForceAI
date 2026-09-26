from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from core.dependencies import get_current_user
from core.db_manager import get_shared_db
from database.shared_models import LLMProvider, LLMModel


def require_platform_admin(user: dict = Depends(get_current_user)) -> dict:
    """Only administrators may inspect or change platform credentials/configuration."""
    if user.get("role") not in ("admin", "enterprise_admin"):
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


def commit_configuration(db: Session) -> None:
    """Do not expose driver exceptions containing bound credential parameters."""
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Unable to save model configuration") from None

router = APIRouter(prefix="/api/v1/platform", tags=["Platform & Models"])

# --- Schemas ---

class ModelCreate(BaseModel):
    provider_id: Optional[int] = None
    name: str
    display_name: str
    type: str = "LLM"
    context_window: str = "4k"
    supports_geo: bool = False
    supports_chat: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    is_default: bool = False
    is_kb_search_default: bool = False

class ModelUpdate(BaseModel):
    display_name: Optional[str] = None
    context_window: Optional[str] = None
    supports_geo: Optional[bool] = None
    supports_chat: Optional[bool] = None
    is_active: Optional[bool] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    is_default: Optional[bool] = None
    is_kb_search_default: Optional[bool] = None

class ModelResponse(BaseModel):
    id: int
    provider_id: Optional[int]
    name: str
    display_name: str
    type: str
    context_window: Optional[str]
    supports_geo: bool
    supports_chat: bool
    is_active: bool
    provider_name: Optional[str] = None
    # Neither credentials nor URLs (which may contain tokens/userinfo) are returned.
    is_default: bool = False
    is_kb_search_default: bool = False

    class Config:
        from_attributes = True

class ProviderCreate(BaseModel):
    name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None

class ProviderResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    models: List[ModelResponse] = []

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.get("/providers", response_model=List[ProviderResponse])
def get_providers(db: Session = Depends(get_shared_db), admin: dict = Depends(require_platform_admin)):
    """List all configured providers and their models"""
    providers = db.query(LLMProvider).filter(LLMProvider.is_active == True).all()
    # Pydantic will handle the relationship serialization
    # Manually populate provider_name for models if needed, but nested model handles it via relationship if struct matches
    # Let's adjust ModelResponse to flattening if needed, but here simple nesting is fine
    return providers

@router.post("/providers", response_model=ProviderResponse)
def create_provider(provider: ProviderCreate, db: Session = Depends(get_shared_db), admin: dict = Depends(require_platform_admin)):
    """Add a new model provider"""
    db_provider = LLMProvider(
        name=provider.name,
        base_url=provider.base_url,
        api_key=provider.api_key
    )
    db.add(db_provider)
    commit_configuration(db)
    db.refresh(db_provider)
    return db_provider

@router.get("/models", response_model=List[ModelResponse])
def get_models(type: Optional[str] = None, geo_only: bool = False, include_inactive: bool = True, db: Session = Depends(get_shared_db), user: dict = Depends(get_current_user)):
    """List all models flat list"""
    # Use outerjoin to include models without a provider (Custom)
    # Default to include all models now (for registry management)
    # The frontend can filter `is_active` itself, or pass explicit False if needed.
    
    query = db.query(LLMModel).outerjoin(LLMProvider)
    
    # Base filter: Only ensure Provider is active IF it exists (optional)
    # Actually, if we want to manage models even if provider is down, we might relax this too.
    # But for now let's just relax the Model.is_active check.
    
    if not include_inactive:
         query = query.filter(LLMModel.is_active == True)

    # We still probably want to filter out models from inactive PROVIDERS? 
    # Or just show them as inactive. 
    # Current logic was:
    # filter(LLMModel.is_active == True, or_(LLMProvider.id == None, LLMProvider.is_active == True))
    
    # New Logic: Get All Models.
    # Frontend handles the "Active" badge.
    
    if type:
        query = query.filter(LLMModel.type == type)
    
    if geo_only:
        query = query.filter(LLMModel.supports_geo == True)
        
    models = query.all()
    
    # Enrich with provider name for table view
    result = []
    for m in models:
        m_dict = ModelResponse.model_validate(m)
        if m.provider:
            m_dict.provider_name = m.provider.name
        else:
            m_dict.provider_name = "Custom / Default"
        result.append(m_dict)
        
    return result

@router.post("/models", response_model=ModelResponse)
def create_model(model: ModelCreate, db: Session = Depends(get_shared_db), admin: dict = Depends(require_platform_admin)):
    # Verify provider if provider_id is provided
    if model.provider_id:
        provider = db.query(LLMProvider).filter(LLMProvider.id == model.provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
    else:
        # Default/System provider fallback could happen here, or leave null
        pass
    
    # Validations
    existing_model = db.query(LLMModel).filter(LLMModel.name == model.name).first()
    if existing_model:
        # Upsert Logic: Whether active or inactive, update it
        # If it was inactive, this effectively reactivates it
        existing_model.is_active = True
        existing_model.display_name = model.display_name
        # model.provider_id might be None for Custom/Preset, keep existing if None or update?
        # The prompt says simple setup, so usually provider_id comes from form (hidden) or None.
        if model.provider_id is not None:
             existing_model.provider_id = model.provider_id
             
        existing_model.type = model.type
        existing_model.context_window = model.context_window
        existing_model.supports_geo = model.supports_geo
        existing_model.supports_chat = model.supports_chat
        
        # A blank or omitted secret must never erase a stored credential.
        if model.api_key:
            existing_model.api_key = model.api_key
        if model.base_url:
            existing_model.base_url = model.base_url
        
        # Handle Defaults
        if model.is_default:
            db.query(LLMModel).filter(LLMModel.is_default == True).update({"is_default": False})
            existing_model.is_default = True
        # If model.is_default is False, we typically don't force unset it unless we want to allow unsetting via edit
        # But this is "Create" endpoint acting as upsert. If user didn't check it, and it was default, should it remain?
        # Safe bet: If user is "Creating", they are providing the Desired State.
        else:
            existing_model.is_default = False
            
        if model.is_kb_search_default:
            db.query(LLMModel).filter(LLMModel.is_kb_search_default == True).update({"is_kb_search_default": False})
            existing_model.is_kb_search_default = True
        else:
            existing_model.is_kb_search_default = False

        commit_configuration(db)
        db.refresh(existing_model)
        return existing_model

    # Handle Defaults: If new model is default, unset others
    if model.is_default:
        db.query(LLMModel).filter(LLMModel.is_default == True).update({"is_default": False})

    # Handle KB Default
    if model.is_kb_search_default:
        db.query(LLMModel).filter(LLMModel.is_kb_search_default == True).update({"is_kb_search_default": False})
        
    db_model = LLMModel(
        provider_id=model.provider_id,
        name=model.name,
        display_name=model.display_name,
        type=model.type,
        context_window=model.context_window,
        supports_geo=model.supports_geo,
        supports_chat=model.supports_chat,
        api_key=model.api_key,
        base_url=model.base_url,
        is_default=model.is_default,
        is_kb_search_default=model.is_kb_search_default
    )
    db.add(db_model)
    commit_configuration(db)
    db.refresh(db_model)
    return db_model

@router.put("/models/{model_id}", response_model=ModelResponse)
def update_model(model_id: int, updates: ModelUpdate, db: Session = Depends(get_shared_db), admin: dict = Depends(require_platform_admin)):
    db_model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
        
    # Handle Default Switch
    if updates.is_default is True:
        db.query(LLMModel).filter(LLMModel.is_default == True).update({"is_default": False})
        db_model.is_default = True
    elif updates.is_default is False:
        db_model.is_default = False

    # Handle KB Default Switch
    if updates.is_kb_search_default is True:
        db.query(LLMModel).filter(LLMModel.is_kb_search_default == True).update({"is_kb_search_default": False})
        db_model.is_kb_search_default = True
    elif updates.is_kb_search_default is False:
        db_model.is_kb_search_default = False

    if updates.display_name is not None: db_model.display_name = updates.display_name
    if updates.context_window is not None: db_model.context_window = updates.context_window
    if updates.supports_geo is not None: db_model.supports_geo = updates.supports_geo
    if updates.supports_chat is not None: db_model.supports_chat = updates.supports_chat
    if updates.is_active is not None: db_model.is_active = updates.is_active
    if updates.api_key: db_model.api_key = updates.api_key
    if updates.base_url: db_model.base_url = updates.base_url
    
    commit_configuration(db)
    db.refresh(db_model)
    return db_model

@router.delete("/models/{model_id}")
def delete_model(model_id: int, db: Session = Depends(get_shared_db), admin: dict = Depends(require_platform_admin)):
    db_model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Hard delete (completely remove from database)
    db.delete(db_model)
    commit_configuration(db)
    return {"message": "Model deleted"}


# --- Skills (Tool Registry) ---

# Tools that are built into the platform (System) vs business tools (Business)
_SYSTEM_TOOLS = {"web_search", "rpa_browser", "ppt_generator"}
_TOOL_TAGS = {
    "check_order_status": ["Unsupported", "No order contract"],
    "get_crm_customer_status": ["Business", "Bound context", "Read-only"],
    "get_crm_quotation_status": ["Business", "Bound context", "Read-only"],
    "web_search": ["System", "Built-in"],
    "rpa_browser": ["System", "Built-in"],
    "ppt_generator": ["System", "Built-in"],
}

@router.get("/skills")
def list_skills():
    """
    List all registered agent skills/tools from the runtime ToolRegistry.
    This is the single source of truth for the 技能工具箱 page.
    """
    from core.tools.registry import ToolRegistry

    schemas = ToolRegistry.get_all_schemas()
    skills = []
    for s in schemas:
        fn = s.get("function", s)  # tolerate both OpenAI-style and flat schemas
        name = fn.get("name", "unknown")
        params = fn.get("parameters", {}) or {}
        required = params.get("required", [])
        properties = params.get("properties", {}) or {}
        skills.append({
            "name": name,
            "description": fn.get("description", ""),
            "category": "system" if name in _SYSTEM_TOOLS else "business",
            "tags": _TOOL_TAGS.get(name, ["Business", "Python"]),
            "parameters": [
                {
                    "name": pname,
                    "type": pdef.get("type", "string"),
                    "description": pdef.get("description", ""),
                    "required": pname in required,
                }
                for pname, pdef in properties.items()
            ],
        })
    return {"skills": skills, "total": len(skills)}


# --- Skills (Tool Registry) ---

# Tools that are built into the platform (System) vs business tools (Business)
_SYSTEM_TOOLS = {"web_search", "rpa_browser", "ppt_generator"}
_TOOL_TAGS = {
    "check_order_status": ["Unsupported", "No order contract"],
    "get_crm_customer_status": ["Business", "Bound context", "Read-only"],
    "get_crm_quotation_status": ["Business", "Bound context", "Read-only"],
    "web_search": ["System", "Built-in"],
    "rpa_browser": ["System", "Built-in"],
    "ppt_generator": ["System", "Built-in"],
}

@router.get("/skills")
def list_skills():
    """
    List all registered agent skills/tools from the runtime ToolRegistry.
    This is the single source of truth for the 技能工具箱 page.
    """
    from core.tools.registry import ToolRegistry

    schemas = ToolRegistry.get_all_schemas()
    skills = []
    for s in schemas:
        fn = s.get("function", s)  # tolerate both OpenAI-style and flat schemas
        name = fn.get("name", "unknown")
        params = fn.get("parameters", {}) or {}
        required = params.get("required", [])
        properties = params.get("properties", {}) or {}
        skills.append({
            "name": name,
            "description": fn.get("description", ""),
            "category": "system" if name in _SYSTEM_TOOLS else "business",
            "tags": _TOOL_TAGS.get(name, ["Business", "Python"]),
            "parameters": [
                {
                    "name": pname,
                    "type": pdef.get("type", "string"),
                    "description": pdef.get("description", ""),
                    "required": pname in required,
                }
                for pname, pdef in properties.items()
            ],
        })
    return {"skills": skills, "total": len(skills)}
