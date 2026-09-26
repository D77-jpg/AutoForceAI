"""Project-scoped digital employees. A mission creates a plan, never executes tools."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from core.agents.planner import MissionPlanner
from core.agents.role_templates import (FORBIDDEN_ACTIONS, TRUSTED_EXECUTABLE_TOOLS,
                                        get_role_template, list_role_templates)
from core.dependencies import get_current_user_id, get_db
from database.models import AgentRole, DigitalEmployee, EmployeeSkill, Mission, Project
from database.shared_models import User

router = APIRouter(prefix="/agents", tags=["digital-employees"])


class StrictPayload(BaseModel):
    class Config:
        extra = "forbid"


class AgentSkillCreate(StrictPayload):
    tool_name: str
    config: dict = Field(default_factory=dict)


class AgentCreate(StrictPayload):
    name: str
    role: AgentRole
    description: str
    system_prompt: str = ""
    capabilities: List[str] = Field(default_factory=list)
    skills: List[AgentSkillCreate] = Field(default_factory=list)


class FromTemplate(StrictPayload):
    template_key: str
    name: Optional[str] = None


class AgentPatch(StrictPayload):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    capabilities: Optional[List[str]] = None
    skills: Optional[List[AgentSkillCreate]] = None
    max_steps: Optional[int] = Field(default=None, ge=1, le=20)
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=600)
    max_cost_usd: Optional[float] = Field(default=None, ge=0, le=5)


class MissionCreate(StrictPayload):
    employee_id: int
    title: str
    objective: str


def _actor(db: Session, user_id: int) -> User:
    actor = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not actor or actor.organization_id is None:
        raise HTTPException(status_code=403, detail="Organization membership required")
    return actor


def _project(db: Session, project_id: int, user_id: int) -> Project:
    actor = _actor(db, user_id)
    project = (db.query(Project).join(User, Project.user_id == User.id)
               .filter(Project.id == project_id, Project.user_id == actor.id,
                       User.organization_id == actor.organization_id).first())
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _employee(db: Session, project_id: int, employee_id: int, user_id: int) -> DigitalEmployee:
    _project(db, project_id, user_id)
    employee = db.query(DigitalEmployee).filter_by(id=employee_id, project_id=project_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


def _skills(skills: List[AgentSkillCreate], allowed_tools: list):
    names = [skill.tool_name for skill in skills]
    if len(names) != len(set(names)) or any(not n or n in FORBIDDEN_ACTIONS or n not in TRUSTED_EXECUTABLE_TOOLS or n not in allowed_tools for n in names):
        raise HTTPException(status_code=422, detail="Unapproved, dangerous or duplicate tool")
    if any(skill.config for skill in skills):
        raise HTTPException(status_code=422, detail="Tool configuration is not authorized")


def _capabilities(capabilities: List[str]):
    # This legacy field has previously been interpreted as executable tool grants.
    # No trusted adapters exist for this workflow: fail closed rather than allowing
    # an unknown action to become available after a future deployment.
    if capabilities:
        raise HTTPException(status_code=422, detail="No executable capabilities are approved")


def _detail(emp):
    return {
        "id": emp.id, "project_id": emp.project_id, "name": emp.name,
        "role": emp.role.value if hasattr(emp.role, "value") else emp.role,
        "description": emp.description, "system_prompt": emp.system_prompt,
        "capabilities": emp.capabilities or [],
        "skills": [{"tool_name": s.tool_name, "config": s.config or {}} for s in emp.skills],
        "template_key": emp.template_key, "template_version": emp.template_version,
        "prompt_version": emp.prompt_version, "allowed_tools": emp.allowed_tools or [],
        "data_scope": emp.data_scope or {}, "max_steps": emp.max_steps,
        "timeout_seconds": emp.timeout_seconds, "max_cost_usd": emp.max_cost_usd,
        "requires_human_approval_for_external_actions": emp.requires_human_approval_for_external_actions,
        "created_by": emp.created_by, "updated_by": emp.updated_by,
        "created_at": emp.created_at, "updated_at": emp.updated_at,
    }


@router.get("/projects")
def list_projects(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    actor = _actor(db, user_id)
    projects = db.query(Project).filter(Project.user_id == actor.id).all()
    return [{"id": p.id, "name": p.name, "organization_id": actor.organization_id} for p in projects]


@router.get("/role-templates")
def role_templates(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    _actor(db, user_id)
    return list_role_templates()


@router.post("/{project_id}/employees/from-template")
def create_from_template(project_id: int, body: FromTemplate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    _project(db, project_id, user_id)
    template = get_role_template(body.template_key)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    name = body.name.strip() if body.name is not None else template["name"]
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    employee = DigitalEmployee(
        project_id=project_id, name=name, role=AgentRole(template["role"]),
        description=template["description"], system_prompt=template["system_prompt"],
        capabilities=[], template_key=template["key"], template_version=template["template_version"],
        prompt_version=template["prompt_version"], allowed_tools=list(template["allowed_tools"]),
        data_scope=dict(template["data_scope"]), max_steps=template["max_steps"],
        timeout_seconds=template["timeout_seconds"], max_cost_usd=template["max_cost_usd"],
        requires_human_approval_for_external_actions=True, created_by=user_id, updated_by=user_id,
    )
    try:
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return _detail(employee)
    except Exception:
        db.rollback()
        raise


@router.post("/{project_id}/employees")
def create_employee(project_id: int, agent: AgentCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    _project(db, project_id, user_id)
    _skills(agent.skills, [])
    _capabilities(agent.capabilities)
    if not agent.name.strip():
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    employee = DigitalEmployee(project_id=project_id, name=agent.name.strip(), role=agent.role,
                               description=agent.description, system_prompt=agent.system_prompt,
                               capabilities=list(agent.capabilities), allowed_tools=[],
                               data_scope={"organization": "authenticated user's current organization", "project": "owned project only", "cross_project": False},
                               requires_human_approval_for_external_actions=True,
                               created_by=user_id, updated_by=user_id)
    try:
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return _detail(employee)
    except Exception:
        db.rollback()
        raise


@router.get("/{project_id}/employees")
def list_employees(project_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    _project(db, project_id, user_id)
    return [_detail(emp) for emp in db.query(DigitalEmployee).filter_by(project_id=project_id).all()]


@router.get("/{project_id}/employees/{employee_id}")
def get_employee(project_id: int, employee_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return _detail(_employee(db, project_id, employee_id, user_id))


@router.patch("/{project_id}/employees/{employee_id}")
def patch_employee(project_id: int, employee_id: int, body: AgentPatch, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    employee = _employee(db, project_id, employee_id, user_id)
    fields = body.model_dump(exclude_unset=True) if hasattr(body, "model_dump") else body.dict(exclude_unset=True)
    if any(value is None for value in fields.values()):
        raise HTTPException(status_code=422, detail="Null fields are not supported")
    if "name" in fields and not fields["name"].strip():
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    if "skills" in fields:
        _skills(body.skills, employee.allowed_tools or [])
    if "capabilities" in fields:
        _capabilities(body.capabilities)
    try:
        for field, value in fields.items():
            if field != "skills":
                setattr(employee, field, value)
        if "skills" in fields:
            employee.skills = [EmployeeSkill(tool_name=s.tool_name, config=s.config) for s in body.skills]
        employee.updated_by = user_id
        employee.updated_at = datetime.now()
        # Editing the prompt is an explicit new revision, never a silent template upgrade.
        if "system_prompt" in fields:
            employee.prompt_version = "custom"
        db.commit()
        db.refresh(employee)
        return _detail(employee)
    except Exception:
        db.rollback()
        raise


@router.post("/missions")
def create_mission(mission: MissionCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    emp = db.query(DigitalEmployee).filter_by(id=mission.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    _project(db, emp.project_id, user_id)
    db_mission = Mission(project_id=emp.project_id, assigned_to=emp.id,
                         title=mission.title, objective=mission.objective)
    db.add(db_mission)
    db.commit()
    db.refresh(db_mission)
    try:
        MissionPlanner(db).create_plan(db_mission.id)
        db.refresh(db_mission)
    except Exception:
        db.rollback()
    return {"id": db_mission.id, "project_id": db_mission.project_id,
            "assigned_to": db_mission.assigned_to, "title": db_mission.title,
            "objective": db_mission.objective, "status": db_mission.status,
            "plan_summary": db_mission.plan_summary, "execution_status": "not_executed"}


@router.get("/missions/{mission_id}")
def get_mission(mission_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    mission = db.query(Mission).filter_by(id=mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    _project(db, mission.project_id, user_id)
    return {"mission": {"id": mission.id, "title": mission.title,
                        "objective": mission.objective, "status": mission.status,
                        "plan_summary": mission.plan_summary, "assigned_to": mission.assigned_to,
                        "execution_status": "not_executed"}, "tasks": mission.tasks}


@router.get("/{project_id}/missions")
def list_project_missions(project_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    _project(db, project_id, user_id)
    return db.query(Mission).filter_by(project_id=project_id).all()
