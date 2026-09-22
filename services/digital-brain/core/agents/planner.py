import json
from sqlalchemy.orm import Session
from database.models import Mission, DigitalEmployee, MissionTask, TaskStatus, MissionStatus
from core.llm.runtime import get_default_llm_model, query_default_llm  # re-exported for service_chat / rag
from .prompts import PLANNING_PROMPT


class MissionPlanner:
    def __init__(self, db: Session):
        self.db = db

    def _query_llm(self, prompt: str) -> str:
        return query_default_llm(self.db, prompt, temperature=0.3)

    def create_plan(self, mission_id: int):
        """
        Generates a breakdown of tasks for a given mission.
        """
        mission = self.db.query(Mission).filter(Mission.id == mission_id).first()
        if not mission or not mission.employee:
            raise ValueError("Mission or assigned employee not found")

        employee = mission.employee

        # Get capabilities from skills relation or JSON fallback
        if hasattr(employee, 'skills') and employee.skills:
            caps_str = ", ".join([s.tool_name for s in employee.skills])
        else:
            caps_str = json.dumps(employee.capabilities, ensure_ascii=False) if employee.capabilities else "General AI Assistance"

        # Prepare Prompt
        prompt = PLANNING_PROMPT.format(
            agent_name=employee.name,
            agent_role=employee.role.value if hasattr(employee.role, 'value') else str(employee.role or "Assistant"),
            capabilities=caps_str,
            objective=mission.objective
        )

        # Call LLM
        print(f"[Planner] Asking LLM to plan for: {mission.title}")
        content = self._query_llm(prompt)

        # Parse JSON
        try:
            # Clean md fences
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            plan_data = json.loads(content)

            # Update Mission
            mission.plan_summary = plan_data.get("summary", "")
            mission.status = MissionStatus.IN_PROGRESS

            # Create Tasks (replace existing)
            self.db.query(MissionTask).filter(MissionTask.mission_id == mission.id).delete()

            tasks = plan_data.get("tasks", [])
            for task in tasks:
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
            print(f"[Planner] Failed to parse plan: {e}")
            print(f"[Planner] Raw content: {content}")
            # Don't crash, just leave mission in planning state with the error recorded
            mission.plan_summary = f"Planning failed: {str(e)}"
            self.db.commit()
            return None
