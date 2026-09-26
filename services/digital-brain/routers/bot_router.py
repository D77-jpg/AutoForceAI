import os
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

# Switch to Tenant DB Models
from core.dependencies import get_db, get_current_user_id
from database.models import DigitalEmployee, EmployeeKB, Project, AgentRole
from database.shared_models import User, LLMModel, KnowledgeBase, KnowledgeDoc # For org checks if needed, but tenant isolation handles most.
from core.db_manager import SharedSessionLocal

router = APIRouter(prefix="/api/v1/bot", tags=["AI Bot"])

# --- Schemas ---

class ModelOption(BaseModel):
    name: str
    display_name: str
    type: str

class ReasoningConfig(BaseModel):
    chain_of_thought: bool = False
    content_structure: Optional[str] = None

class BotCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    model_name: Optional[str] = "zhipu-glm-4"
    kb_search_behavior: Optional[str] = "fallback_to_llm"
    kb_ids: List[int] = [] # Multi-select support
    reasoning_config: Optional[ReasoningConfig] = None
    is_visible_on_landing: bool = False

class BotResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = ""
    system_prompt: Optional[str] = ""
    welcome_message: Optional[str] = ""
    model_name: Optional[str] = ""
    kb_search_behavior: Optional[str] = "fallback_to_llm"
    kb_ids: List[int] = []
    kb_names: List[str] = [] # Added for UI display
    kb_file_names: List[str] = [] # Added for UI card display
    reasoning_config: Optional[Dict[str, Any]] = {}
    is_visible_on_landing: bool = False
    created_at: Optional[datetime] = None

# --- Endpoints ---

@router.delete("/{bot_id}")
def delete_bot(
    bot_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    emp = db.query(DigitalEmployee).join(Project).filter(
        DigitalEmployee.id == bot_id,
        Project.user_id == user_id
    ).first()
    
    if not emp:
        raise HTTPException(status_code=404, detail="Bot not found or access denied")
    
    # 1. Delete relations (EmployeeKB) - handled by cascade usually, or manual
    db.query(EmployeeKB).filter(EmployeeKB.employee_id == bot_id).delete()
    
    # 2. Delete Bot
    db.delete(emp)
    db.commit()
    
    return {"message": "Bot deleted successfully", "id": bot_id}

@router.get("/models", response_model=List[ModelOption])
def list_available_models():
    """
    List all available LLM models configured in the system (Shared Model Registry).
    """
    db = SharedSessionLocal()
    try:
        models = db.query(LLMModel).filter(LLMModel.type.in_(["LLM", "Chat"])).all()
        # Fallback if no models seeded
        if not models:
            return [
                {"name": "zhipu-glm-4", "display_name": "Zhipu GLM-4 (Default)", "type": "LLM"},
                {"name": "qwen-turbo", "display_name": "Qwen Turbo", "type": "LLM"},
                {"name": "gpt-4", "display_name": "GPT-4", "type": "LLM"}
            ]
        
        return [
            ModelOption(
                name=m.name,
                display_name=m.display_name or m.name,
                type=m.type
            ) for m in models
        ]
    finally:
        db.close()

@router.get("/", response_model=List[BotResponse])
def list_bots(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db) 
):
    # List Digital Employees in Tenant DB (Scoped to User's Projects)
    employees = db.query(DigitalEmployee).join(Project).filter(Project.user_id == user_id).all()
    
    # Shared DB for KBs
    shared_db = SharedSessionLocal()

    result = []
    try:
        for emp in employees:
            # Resolve KBs
            kb_ids_list = []
            kb_names = []
            kb_file_names = []
            
            if emp.knowledge_bases:
                for ekb in emp.knowledge_bases:
                    if ekb.kb_id and ekb.kb_id.isdigit():
                         kb_ids_list.append(int(ekb.kb_id))
            
            # Fetch Names and File Names for KBs
            if kb_ids_list:
                # 1. Get KB Names
                kbs = shared_db.query(KnowledgeBase.name)\
                               .filter(KnowledgeBase.id.in_(kb_ids_list))\
                               .all()
                kb_names = [k.name for k in kbs]

                # 2. Get Docs associated with these KBs (limit to 3 for UI efficiency)
                # Note: This finds docs in ANY of the KBs.
                docs = shared_db.query(KnowledgeDoc.filename)\
                                .filter(KnowledgeDoc.kb_id.in_(kb_ids_list))\
                                .limit(3)\
                                .all()
                kb_file_names = [d.filename for d in docs]

            welcome_msg = "你好！"
            if emp.capabilities and isinstance(emp.capabilities, dict):
                 welcome_msg = emp.capabilities.get("welcome_message", "你好！")
            
            # Reasoning config
            r_config = emp.reasoning_config or {}

            result.append(BotResponse(
                id=emp.id,
                name=emp.name,
                description=emp.description,
                system_prompt=emp.system_prompt,
                welcome_message=welcome_msg,
                model_name=emp.model_name,
                kb_search_behavior=emp.kb_search_behavior,
                kb_ids=kb_ids_list,
                kb_names=kb_names,
                kb_file_names=kb_file_names,
                reasoning_config=r_config,
                is_visible_on_landing=emp.is_visible_on_landing or False,
                created_at=None 
            ))
    except Exception as e:
        print("Bot listing failed")
        # Return partial results or re-raise?
        # Re-raising 500 might trigger alert, better to log and return what we have? 
        # But for now, let's allow it to fail to debug if needed.
        raise e
    finally:
        shared_db.close()

    return result

@router.post("/", response_model=BotResponse)
def create_bot(
    request: BotCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    # Get user's default project
    project = db.query(Project).filter(Project.user_id == user_id).first()
    if not project:
         # Auto-create default project for tenant
         project = Project(name="Default Project", user_id=user_id)
         db.add(project)
         db.commit()
         db.refresh(project)

    # Prepare capabilities
    capabilities = {"welcome_message": request.welcome_message or "你好！"}
    
    # Check duplicate name within the user's project
    existing_bot = db.query(DigitalEmployee).join(Project).filter(
        DigitalEmployee.name == request.name,
        Project.user_id == user_id
    ).first()
    
    if existing_bot:
        raise HTTPException(status_code=400, detail="Bot name already exists in your workspace")
    
    new_emp = DigitalEmployee(
        project_id=project.id,
        name=request.name,
        role=AgentRole.EXECUTOR, # Default
        description=request.description,
        system_prompt=request.system_prompt,
        model_name=request.model_name,
        kb_search_behavior=request.kb_search_behavior,
        reasoning_config=request.reasoning_config.dict() if request.reasoning_config else {},
        is_visible_on_landing=request.is_visible_on_landing,
        capabilities=capabilities,
        avatar_url=""
    )
    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)
    
    # KBs
    for kid in request.kb_ids:
        kb_link = EmployeeKB(employee_id=new_emp.id, kb_id=str(kid))
        db.add(kb_link)
    db.commit()
    
    return {
        "id": new_emp.id,
        "name": new_emp.name,
        "description": new_emp.description,
        "system_prompt": new_emp.system_prompt,
        "welcome_message": capabilities["welcome_message"],
        "model_name": new_emp.model_name,
        "kb_search_behavior": new_emp.kb_search_behavior,
        "kb_ids": request.kb_ids,
        "reasoning_config": new_emp.reasoning_config,
        "is_visible_on_landing": new_emp.is_visible_on_landing,
        "created_at": None
    }

@router.patch("/{bot_id}", response_model=BotResponse)
def update_bot(
    bot_id: int,
    request: BotCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    emp = db.query(DigitalEmployee).join(Project).filter(
        DigitalEmployee.id == bot_id,
        Project.user_id == user_id
    ).first()
    
    if not emp:
        raise HTTPException(status_code=404, detail="Bot not found or access denied")
        
    # Check duplicate name if name changed (Scoped to user)
    if request.name != emp.name:
        existing_bot = db.query(DigitalEmployee).join(Project).filter(
            DigitalEmployee.name == request.name,
            DigitalEmployee.id != bot_id,
            Project.user_id == user_id
        ).first()
        if existing_bot:
            raise HTTPException(status_code=400, detail="Bot name already exists")
    
    emp.name = request.name
    emp.description = request.description
    emp.system_prompt = request.system_prompt
    emp.model_name = request.model_name
    emp.kb_search_behavior = request.kb_search_behavior
    emp.is_visible_on_landing = request.is_visible_on_landing
    
    if request.reasoning_config:
        emp.reasoning_config = request.reasoning_config.dict()
        
    # Update Welcome Message in capabilities
    if request.welcome_message:
        caps = emp.capabilities
        if not caps or not isinstance(caps, dict):
            caps = {}
        caps["welcome_message"] = request.welcome_message
        emp.capabilities = caps
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(emp, "capabilities")
    
    # Ensure reasoning_config changes are tracked if needed (though assignment should be enough)
    if request.reasoning_config:
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(emp, "reasoning_config")

    # Update KBs (Replace logic)
    # Clear existing
    db.query(EmployeeKB).filter(EmployeeKB.employee_id == emp.id).delete()
    # Add new
    for kid in request.kb_ids:
        kb_link = EmployeeKB(employee_id=emp.id, kb_id=str(kid))
        db.add(kb_link)
        
    db.commit()
    db.refresh(emp)

    # Re-fetch KBs
    kb_ids = []
    for ekb in emp.knowledge_bases:
        if ekb.kb_id and ekb.kb_id.isdigit():
            kb_ids.append(int(ekb.kb_id))

    return {
        "id": emp.id,
        "name": emp.name,
        "description": emp.description,
        "system_prompt": emp.system_prompt,
        "welcome_message": emp.capabilities.get("welcome_message", ""),
        "model_name": emp.model_name,
        "kb_search_behavior": emp.kb_search_behavior,
        "kb_ids": kb_ids,
        "reasoning_config": emp.reasoning_config,
        "is_visible_on_landing": emp.is_visible_on_landing,
        "created_at": None
    }
@router.get("/{bot_id}", response_model=BotResponse)
def get_bot_details(
    bot_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific Digital Employee (Scoped to User).
    """
    emp = db.query(DigitalEmployee).join(Project).filter(
        DigitalEmployee.id == bot_id,
        Project.user_id == user_id
    ).first()
    
    if not emp:
        raise HTTPException(status_code=404, detail="Bot not found")

    # Resolve KBs
    kb_ids_list = []
    if emp.knowledge_bases:
        for ekb in emp.knowledge_bases:
            if ekb.kb_id and ekb.kb_id.isdigit():
                kb_ids_list.append(int(ekb.kb_id))

    welcome_msg = "你好！"
    if emp.capabilities and isinstance(emp.capabilities, dict):
        welcome_msg = emp.capabilities.get("welcome_message", "你好！")
    
    # Reasoning config
    r_config = emp.reasoning_config or {}
    
    # KB File Names
    kb_file_names = []
    if kb_ids_list:
        shared_db = SharedSessionLocal()
        try:
            docs = shared_db.query(KnowledgeDoc.filename)\
                            .filter(KnowledgeDoc.kb_id.in_(kb_ids_list))\
                            .limit(10)\
                            .all()
            kb_file_names = [d.filename for d in docs]
        finally:
            shared_db.close()

    return BotResponse(
        id=emp.id,
        name=emp.name,
        description=emp.description,
        system_prompt=emp.system_prompt,
        welcome_message=welcome_msg,
        model_name=emp.model_name,
        kb_search_behavior=emp.kb_search_behavior,
        kb_ids=kb_ids_list,
        kb_file_names=kb_file_names,
        reasoning_config=r_config,
        is_visible_on_landing=emp.is_visible_on_landing,
        created_at=None 
    )