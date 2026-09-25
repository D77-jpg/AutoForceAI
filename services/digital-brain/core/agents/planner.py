import json
from sqlalchemy.orm import Session
from database.models import Mission, DigitalEmployee, MissionTask, TaskStatus, MissionStatus
from core.llm.runtime import get_default_llm_model, query_default_llm  # legacy re-exports; not used for mission execution
from .prompts import PLANNING_PROMPT
from .role_templates import TRUSTED_EXECUTABLE_TOOLS


class MissionPlanner:
    def __init__(self, db: Session):
        self.db = db

    def _query_llm(self, prompt: str) -> str:
        # Existing provider/fallback calls have no enforceable monetary accounting
        # and no reliably cancellable request timeout. Fail closed rather than
        # spending beyond the persisted employee limits or claiming an SLA.
        raise RuntimeError("Planning unavailable: LLM timeout and cost limits cannot be enforced")

    def create_plan(self, mission_id: int):
        """
        Generates a breakdown of tasks for a given mission.
        """
        mission = self.db.query(Mission).filter(Mission.id == mission_id).first()
        if not mission or not mission.employee:
            raise ValueError("Mission or assigned employee not found")

        employee = mission.employee

        # Stored skills are never executable grants. Ignore unapproved legacy rows.
        safe_tools = set(employee.allowed_tools or []) & TRUSTED_EXECUTABLE_TOOLS
        caps_str = ", ".join(s.tool_name for s in employee.skills if s.tool_name in safe_tools) or "no executable tools available"

        # Prepare Prompt
        prompt = PLANNING_PROMPT
        for key, value in {
            "agent_name": employee.name,
            "agent_role": employee.role.value if hasattr(employee.role, 'value') else str(employee.role or "Assistant"),
            "capabilities": caps_str,
            "objective": mission.objective,
        }.items():
            prompt = prompt.replace("{" + key + "}", str(value))

        # Planning is unavailable unless the model adapter can enforce limits.
        # Keep failures in the mission record without exposing raw prompt/content.
        content = ""
        try:
            content = self._query_llm(prompt)
            # Clean md fences
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            plan_data = json.loads(content)

            # Update Mission
            mission.plan_summary = "PLAN ONLY — NOT EXECUTED. " + str(plan_data.get("summary", ""))
            mission.status = MissionStatus.PLANNING

            # Create Tasks (replace existing)
            self.db.query(MissionTask).filter(MissionTask.mission_id == mission.id).delete()

            tasks = plan_data.get("tasks", [])
            if not isinstance(tasks, list) or len(tasks) > min(employee.max_steps or 5, 20):
                raise ValueError("Invalid plan size")
            safe_types = {"research", "analysis", "generate_content"}
            for task in tasks:
                if not isinstance(task, dict) or task.get("type") not in safe_types:
                    raise ValueError("Plan contains unknown or unsafe action")
                db_task = MissionTask(
                    mission_id=mission.id,
                    title=task.get("title"),
                    description=task.get("description"),
                    task_type=task.get("type", "analysis"),
                    order_index=task.get("step", 1),
                    dependency_task_ids=task.get("dependencies", []),
                    status=TaskStatus.PENDING
                )
                self.db.add(db_task)

            self.db.commit()
            print(f"[Planner] Plan created with {len(tasks)} tasks.")
            return plan_data

        except Exception as e:
            print("[Planner] Plan rejected; see mission status (content omitted)")
            # Don't crash, just leave mission in planning state with the error recorded
            mission.plan_summary = f"Planning failed: {str(e)}"
            self.db.commit()
            return None
