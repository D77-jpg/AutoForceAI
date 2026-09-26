"""Best-effort LLM request metering without persisting secrets or error bodies."""
from datetime import datetime, timezone
import re

from sqlalchemy.orm import Session

from core.db_manager import SharedSessionLocal
from database.shared_models import LLMRequestLog

_SAFE_CATEGORY = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


class CostMonitor:
    @staticmethod
    def log_request(
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        status: str = "success",
        error_msg: str | None = None,
        user_id: int | None = None,
        trace_id: str | None = None,
        error_category: str | None = None,
        cost_usd: float | None = None,
    ) -> None:
        """Persist verified usage; never store raw exceptions, prompts or credentials.

        Without provider-supplied or configured verified price, cost is unknown.
        `error_msg` is accepted for backwards compatibility but intentionally ignored.
        """
        category = (error_category or "UNKNOWN").upper() if status != "success" else None
        if category and not _SAFE_CATEGORY.fullmatch(category):
            category = "UNKNOWN"
        # An arbitrary caller cannot claim a price without an independently
        # verified pricing source; leave the field unknown until one is wired.
        db: Session = SharedSessionLocal()
        try:
            db.add(LLMRequestLog(
                provider=provider or "unknown", model=model or "unknown",
                input_tokens=max(0, int(input_tokens or 0)),
                output_tokens=max(0, int(output_tokens or 0)),
                total_tokens=max(0, int(input_tokens or 0)) + max(0, int(output_tokens or 0)),
                latency_ms=max(0, int(latency_ms or 0)),
                status="success" if status == "success" else "error",
                error_category=category, error_msg=None, cost_usd=None,
                user_id=user_id, trace_id=trace_id,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            ))
            db.commit()
        except Exception:
            db.rollback()  # Monitoring must not break a completed business call.
        finally:
            db.close()
