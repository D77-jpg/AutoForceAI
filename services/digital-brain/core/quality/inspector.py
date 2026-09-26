from typing import List, Dict, Any
import json
from datetime import datetime
from sqlalchemy.orm import Session
from loguru import logger

from database.shared_models import BrainSession, BrainMessage, QualityRule, InspectionRecord
from core.llm.attribution import UNKNOWN
from core.llm.runtime import query_default_llm_with_attribution

class SessionInspector:
    def __init__(self, db: Session):
        self.db = db
        # Select the configured model at request time; no hardcoded judge model.
        
    def inspect(self, session_id: int) -> InspectionRecord:
        """
        Run AI Inspection for a given session.
        """
        logger.info(f"[Inspector] Starting inspection for Session {session_id}")
        
        # 1. Fetch Data
        session = self.db.query(BrainSession).filter(BrainSession.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")
            
        messages = self.db.query(BrainMessage).filter(BrainMessage.session_id == session_id).order_by(BrainMessage.created_at).all()
        rules = self.db.query(QualityRule).filter(QualityRule.is_active == True).all()
        
        if not messages:
            logger.warning("Empty session, skipping.")
            return None

        # 2. Construct Prompt
        transcript = self._format_transcript(messages)
        rubric = self._format_rubric(rules)
        
        prompt = f"""
        你是一位专业的客服质检专家 (Quality Assurance Specialist)。请根据以下[对话记录]和[质检标准]，对客服的表现进行评分。
        
        ### 对话记录 (Transcript)
        {transcript}
        
        ### 质检标准 (SOP Rubric)
        {rubric}
        
        ### 任务要求
        1. 对每一项规则进行打分（满分=权重值）。
        2. 如果发现问题，必须引用原话作为证据。
        3. 计算总分（满分100，根据各项权重归一化计算）。
        4. 给出最终评级 (Excellent > 90, Good > 80, Warning > 60, Critical < 60)。
        5. 以 JSON 格式输出结果。
        
        ### 输出格式 (JSON Only)
        {{
            "total_score": 85.5,
            "status": "Good",
            "issues": [
                 {{ "rule": "礼貌与态度", "deduction": 2, "reason": "第3轮回复中语气略显生硬", "evidence": "你是听不懂吗" }}
            ],
            "suggestion": "整体表现尚可，但在处理用户反复追问时缺乏耐心，建议使用'我理解您的焦急'等共情话术。"
        }}
        """
        
        # 3. Call LLM
        logger.info("[Inspector] Sending to LLM...")
        try:
            # Keep provenance from the actual remote response, not configuration.
            attribution = query_default_llm_with_attribution(self.db, prompt, temperature=0.1)
            result = json.loads(self._clean_json(attribution.content))
            if not isinstance(result, dict):
                raise ValueError("Inspection response must be an object")
            
            # 4. Save Record
            record = InspectionRecord(
                session_id=session_id,
                total_score=result.get("total_score", 0),
                status=result.get("status", "Warning"),
                issues=result.get("issues", []),
                suggestion=result.get("suggestion", ""),
                model_used=attribution.model,
                model_provider=attribution.provider,
                model_request_id=attribution.request_id,
            )
            
            # Remove old record if exists
            old_record = self.db.query(InspectionRecord).filter(InspectionRecord.session_id == session_id).first()
            if old_record:
                self.db.delete(old_record)
                
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            
            logger.info(f"[Inspector] Inspection Completed. Score: {record.total_score}")
            return record

        except Exception:
            # A rejected/invalid answer is not attributable to a completed response.
            # Never persist the configured model as if it actually answered.
            self.db.rollback()
            failure = InspectionRecord(
                session_id=session_id, total_score=0, status="Failed", issues=[],
                suggestion="Inspection failed; no validated evaluation is available.",
                model_used=UNKNOWN, model_provider=UNKNOWN, model_request_id=None,
            )
            previous = self.db.query(InspectionRecord).filter(InspectionRecord.session_id == session_id).first()
            if previous:
                self.db.delete(previous)
            self.db.add(failure)
            self.db.commit()
            self.db.refresh(failure)
            logger.warning("[Inspector] Inspection failed; provider response not attributed")
            return failure

    def _format_transcript(self, messages: List[BrainMessage]) -> str:
        text = ""
        for i, msg in enumerate(messages):
            role_name = "用户" if msg.role == "user" else "客服AI"
            text += f"[{i+1}] {role_name}: {msg.content}\n"
        return text

    def _format_rubric(self, rules: List[QualityRule]) -> str:
        text = ""
        for rule in rules:
            text += f"- 【{rule.name}】 (权重: {rule.weight})\n  定义: {rule.description}\n"
        return text
    
    def _clean_json(self, text: str) -> str:
        # Simple cleaner for Markdown code blocks
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
