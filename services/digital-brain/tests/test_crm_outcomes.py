"""阶段 2 Wave D：成交/流失回流轮询测试。

运行（services/digital-brain 目录）：
    venv/Scripts/python -m pytest tests/test_crm_outcomes.py -q
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401
from core.db_manager import SHARED_ENGINE, SharedSessionLocal  # noqa: E402
from core.crm.client import CrmApiError  # noqa: E402
from core.crm.contract import OutcomeEvent, OutcomeFeedResponse  # noqa: E402
from core.crm.outcome_poller import _apply_event, poll_all_outcomes, poll_org_outcomes  # noqa: E402
from database.base import Base  # noqa: E402
from database.shared_models import (  # noqa: E402
    CrmEntityLink,
    CrmIntegrationConfig,
    CrmOutcomeEvent,
    Lead,
    Organization,
)

PROJECT = "66cf2f1a9b2c4d5e6f708192"


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=SHARED_ENGINE)
    session = SharedSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=SHARED_ENGINE)


@pytest.fixture()
def setup(db):
    org = Organization(name=f"org-{datetime.now().timestamp()}")
    db.add(org)
    db.flush()
    cfg = CrmIntegrationConfig(
        organization_id=org.id, base_url="http://crm.local/api",
        project_id=PROJECT, service_token="gci_test", enabled=True,
        last_health_status="ok",
    )
    lead = Lead(organization_id=org.id, email="buyer@x.com", name="Buyer",
                source="Website AI Chat", status="contacted")
    db.add_all([cfg, lead])
    db.flush()
    link = CrmEntityLink(
        organization_id=org.id, lead_id=lead.id, provider="genesis_crm",
        project_id=PROJECT, remote_customer_id="cust-1",
    )
    db.add(link)
    db.commit()
    return {"org": org, "cfg": cfg, "lead": lead, "link": link}


def _event(event_id: str, to_status: str, customer_id="cust-1", external_id="lead:1", cursor=None):
    return OutcomeEvent(
        eventId=event_id,
        cursor=cursor or f"cursor-{event_id}",
        customerId=customer_id,
        externalId=external_id,
        fromStatus="negotiating",
        toStatus=to_status,
        occurredAt=datetime(2026, 9, 23, 1, 0, 0),
    )


class FakePollClient:
    def __init__(self, *pages):
        self.pages = list(pages)
        self.calls: list = []

    def fetch_outcomes(self, cursor=None, limit=50):
        self.calls.append(cursor)
        page = self.pages.pop(0)
        if isinstance(page, Exception):
            raise page
        return page


def _feed(items, next_cursor=None, has_more=False):
    return OutcomeFeedResponse(items=items, nextCursor=next_cursor, hasMore=has_more)


def test_won_event_marks_lead_converted_and_keeps_source(db, setup):
    lead, cfg = setup["lead"], setup["cfg"]
    client = FakePollClient(_feed([_event("ev-1", "won")], next_cursor="cursor-ev-1"))
    processed = poll_org_outcomes(db, cfg, client=client)

    assert processed == 1
    db.expire_all()
    lead = db.query(Lead).filter_by(id=lead.id).one()
    assert lead.status == "converted"               # 成交归因
    assert lead.source == "Website AI Chat"          # 获客来源不被 CRM 覆盖
    link = db.query(CrmEntityLink).filter_by(id=setup["link"].id).one()
    assert link.remote_status == "won"
    assert db.query(CrmOutcomeEvent).filter_by(event_id="ev-1").count() == 1
    assert cfg.outcome_cursor == "cursor-ev-1"       # 游标前进


def test_replayed_event_is_idempotent(db, setup):
    cfg = setup["cfg"]
    page = _feed([_event("ev-2", "won")], next_cursor="cursor-ev-2")
    poll_org_outcomes(db, cfg, client=FakePollClient(page))
    # 同一事件再次出现在 feed（服务侧重放/游标回退）
    processed = poll_org_outcomes(db, cfg, client=FakePollClient(page))
    assert processed == 0
    assert db.query(CrmOutcomeEvent).filter_by(event_id="ev-2").count() == 1


def test_lost_event_updates_summary_only(db, setup):
    lead, cfg = setup["lead"], setup["cfg"]
    processed = poll_org_outcomes(db, cfg, client=FakePollClient(_feed([_event("ev-3", "lost")])))

    assert processed == 1
    db.expire_all()
    assert db.query(Lead).filter_by(id=lead.id).one().status == "contacted"  # lost 不改本地状态
    assert db.query(CrmEntityLink).filter_by(id=setup["link"].id).one().remote_status == "lost"


def test_event_without_local_link_is_recorded_not_crash(db, setup):
    cfg = setup["cfg"]
    processed = poll_org_outcomes(
        db, cfg,
        client=FakePollClient(_feed([_event("ev-4", "won", customer_id="cust-unknown", external_id=None)])),
    )
    assert processed == 1
    ev = db.query(CrmOutcomeEvent).filter_by(event_id="ev-4").one()
    assert ev.lead_id is None


def test_same_remote_customer_never_crosses_organization_boundary(db, setup):
    """即使配置异常地指向同一项目/客户，也不能污染另一组织的映射与线索。"""
    other_org = Organization(name=f"org-other-{datetime.now().timestamp()}")
    db.add(other_org)
    db.flush()
    foreign_cfg = CrmIntegrationConfig(
        organization_id=other_org.id,
        base_url="http://crm.local/api",
        project_id=PROJECT,
        service_token="gci_test",
    )

    assert _apply_event(db, foreign_cfg, _event("ev-cross-org", "won")) is True
    db.commit()
    db.expire_all()

    lead = db.query(Lead).filter_by(id=setup["lead"].id).one()
    link = db.query(CrmEntityLink).filter_by(id=setup["link"].id).one()
    event = db.query(CrmOutcomeEvent).filter_by(
        organization_id=other_org.id,
        event_id="ev-cross-org",
    ).one()
    assert lead.status == "contacted"
    assert link.remote_status is None
    assert event.lead_id is None


def test_batch_commit_cursor_not_advanced_on_failure(db, setup):
    """第二页失败：第一页事件已提交且游标停在第一页末尾，重放从断点继续。"""
    cfg = setup["cfg"]
    page1 = _feed([_event("ev-5", "won")], next_cursor="cursor-ev-5", has_more=True)
    client = FakePollClient(page1, CrmApiError("boom", retryable=True))

    with pytest.raises(CrmApiError):
        poll_org_outcomes(db, cfg, client=client)

    db.expire_all()
    assert db.query(CrmOutcomeEvent).filter_by(event_id="ev-5").count() == 1
    assert cfg.outcome_cursor == "cursor-ev-5"  # 只前进到已提交的批次

    # 恢复后从断点继续拿第二页
    page2 = _feed([_event("ev-6", "lost")], next_cursor="cursor-ev-6")
    poll_org_outcomes(db, cfg, client=FakePollClient(page2))
    assert db.query(CrmOutcomeEvent).filter_by(event_id="ev-6").count() == 1


def test_auth_invalid_pauses_polling(db, setup):
    cfg = setup["cfg"]
    poll_all_outcomes_client = FakePollClient(
        CrmApiError("凭证失效", code="UNAUTHORIZED", http_status=401, auth_invalid=True)
    )

    import core.crm.outcome_poller as poller
    original = poller.client_from_config
    poller.client_from_config = lambda *a, **k: poll_all_outcomes_client
    try:
        poll_all_outcomes(db)
    finally:
        poller.client_from_config = original

    db.expire_all()
    assert cfg.last_health_status == "auth_invalid"

    # 暂停期间不再发起 HTTP 调用
    poll_all_outcomes(db)
    assert len(poll_all_outcomes_client.calls) == 1
