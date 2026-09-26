"""H-06: permission, snapshot, atomicity, and plan-only regression tests."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.dependencies import get_current_user_id, get_db
from database.base import Base
from database.models import DigitalEmployee, EmployeeSkill, Mission, Project
from database.shared_models import Organization, User
from routers.agent_router import router


@pytest.fixture
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add_all([Organization(id=1, name="one"), Organization(id=2, name="two")])
    db.flush()
    db.add_all([User(id=1, username="a", organization_id=1, is_active=True),
                User(id=2, username="b", organization_id=2, is_active=True),
                User(id=3, username="c", organization_id=1, is_active=True)])
    db.flush()
    db.add_all([Project(id=10, user_id=1, name="mine"), Project(id=20, user_id=2, name="other org"),
                Project(id=30, user_id=3, name="other owner")])
    db.commit()
    app = FastAPI()
    app.include_router(router)
    current = {"id": 1}
    app.dependency_overrides[get_current_user_id] = lambda: current["id"]
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app), db, current
    db.close()
    engine.dispose()


def test_catalog_and_project_boundary(env):
    client, db, user = env
    templates = client.get("/agents/role-templates").json()
    assert len(templates) == 5
    assert {t["key"] for t in templates} == {"lead_researcher", "sales_development", "followup_coordinator", "quote_assistant", "customer_support"}
    assert all(t["allowed_tools"] == [] and t["unavailable_capabilities"] and t["requires_human_approval_for_external_actions"] for t in templates)
    assert [p["id"] for p in client.get("/agents/projects").json()] == [10]
    for project in (20, 30, 999):
        assert client.post(f"/agents/{project}/employees/from-template", json={"template_key": "lead_researcher"}).status_code == 404
        assert client.get(f"/agents/{project}/employees").status_code == 404
        assert client.get(f"/agents/{project}/missions").status_code == 404
    assert db.query(DigitalEmployee).count() == 0


def test_template_create_edit_is_snapshot_and_rejects_tools(env):
    client, db, user = env
    url = "/agents/10/employees"
    created = client.post(url + "/from-template", json={"template_key": "lead_researcher", "name": "  Scout  "})
    assert created.status_code == 200, created.text
    data = created.json()
    assert data["name"] == "Scout" and data["template_version"] == "1.0.0"
    assert data["created_by"] == 1 and data["allowed_tools"] == []
    emp_url = url + f"/{data['id']}"
    assert client.get(emp_url).json()["id"] == data["id"]
    assert len(client.get(url).json()) == 1
    for tool in ("send_email", "rpa_action", "unknown_tool", "web_search"):
        response = client.patch(emp_url, json={"name": "MUTATED", "skills": [{"tool_name": tool, "config": {}}]})
        assert response.status_code == 422, response.text
        assert client.get(emp_url).json()["name"] == "Scout"
    assert client.patch(emp_url, json={"max_steps": 21}).status_code == 422
    assert client.patch(emp_url, json={"capabilities": ["unknown_action"]}).status_code == 422
    assert client.post(url, json={"name": "x", "role": "strategist", "description": "x", "capabilities": ["unknown_action"]}).status_code == 422
    assert client.patch(emp_url, json={"requires_human_approval_for_external_actions": False}).status_code == 422
    assert client.get(emp_url).json()["requires_human_approval_for_external_actions"] is True
    edited = client.patch(emp_url, json={"name": "New", "system_prompt": "Only drafts", "max_steps": 3})
    assert edited.status_code == 200
    assert edited.json()["prompt_version"] == "custom"
    assert edited.json()["template_version"] == "1.0.0"
    assert client.get("/agents/role-templates").json()[0]["name"] == "线索研究员"
    assert client.get(emp_url.replace("/10/", "/20/")).status_code == 404
    assert db.query(EmployeeSkill).count() == 0


def test_legacy_create_and_mission_access(env, monkeypatch):
    client, db, user = env
    payload = {"name": "legacy", "role": "strategist", "description": "draft"}
    assert client.post("/agents/20/employees", json=payload).status_code == 404
    assert client.post("/agents/10/employees", json={**payload, "skills": [{"tool_name": "send_email"}]}).status_code == 422
    result = client.post("/agents/10/employees", json=payload)
    assert result.status_code == 200, result.text
    employee_id = result.json()["id"]
    monkeypatch.setattr("routers.agent_router.MissionPlanner.create_plan", lambda self, mission_id: None)
    user["id"] = 2
    assert client.get(f"/agents/10/employees/{employee_id}").status_code == 404
    assert client.patch(f"/agents/10/employees/{employee_id}", json={"name": "hijack"}).status_code == 404
    assert client.post("/agents/missions", json={"employee_id": employee_id, "title": "x", "objective": "x"}).status_code == 404
    assert db.query(Mission).count() == 0
    user["id"] = 1
    mission = client.post("/agents/missions", json={"employee_id": employee_id, "title": "plan", "objective": "draft"})
    assert mission.status_code == 200, mission.text
    mission_id = mission.json()["id"]
    user["id"] = 2
    assert client.get(f"/agents/missions/{mission_id}").status_code == 404
    assert db.query(Mission).count() == 1


def test_default_planning_fails_closed_without_spending(env, monkeypatch):
    client, db, _ = env
    employee = client.post("/agents/10/employees/from-template", json={"template_key": "lead_researcher"}).json()
    def must_not_call(*args, **kwargs):
        raise AssertionError("Unmetered model was invoked")
    monkeypatch.setattr("core.agents.planner.query_default_llm", must_not_call)
    response = client.post("/agents/missions", json={"employee_id": employee["id"], "title": "plan", "objective": "plan"})
    assert response.status_code == 200
    assert "timeout and cost limits cannot be enforced" in response.json()["plan_summary"]
    assert response.json()["execution_status"] == "not_executed"
    assert db.query(Mission).count() == 1


def test_planner_rejects_dangerous_and_unknown_task_types(env, monkeypatch):
    client, db, user = env
    employee = client.post("/agents/10/employees/from-template", json={"template_key": "lead_researcher"}).json()
    from core.agents.planner import MissionPlanner
    for action in ("send_email", "rpa_action", "unknown"):
        monkeypatch.setattr(MissionPlanner, "_query_llm", lambda self, prompt: '{"summary":"done", "tasks":[{"type":"' + action + '","title":"x"}]}')
        response = client.post("/agents/missions", json={"employee_id": employee["id"], "title": "plan", "objective": "plan"})
        assert response.status_code == 200, response.text
        assert "id" in response.json(), response.json()
        mission = db.query(Mission).filter_by(id=response.json()["id"]).one()
        assert mission.status.value == "planning" and not mission.tasks
        assert "Planning failed" in mission.plan_summary
    monkeypatch.setattr(MissionPlanner, "_query_llm", lambda self, prompt: '{"summary":"draft", "tasks":[{"type":"analysis","title":"think"}]}')
    response = client.post("/agents/missions", json={"employee_id": employee["id"], "title": "plan", "objective": "plan"})
    assert response.status_code == 200
    mission = db.query(Mission).filter_by(id=response.json()["id"]).one()
    assert mission.status.value == "planning" and "NOT EXECUTED" in mission.plan_summary
    assert len(mission.tasks) == 1
