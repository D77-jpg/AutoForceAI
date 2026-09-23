"""Wave D 端到端验证：Genesis 改 won → AutoForceAI 一个轮询周期内成交归因。

前置：Genesis server 运行于 :5000（admin/123456 为本地开发默认值）。
用法：venv/Scripts/python -X utf8 scripts/e2e_wave_d.py
"""
import os
import sys
import tempfile
import time

import requests

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "e2ed.db").replace("\\", "/")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.models  # noqa: F401
from core.db_manager import SHARED_ENGINE, SharedSessionLocal
from core.crm import dispatcher
from core.crm.client import GenesisCRMClient
from core.crm.outcome_poller import poll_org_outcomes
from database.base import Base
from database.shared_models import CrmEntityLink, CrmIntegrationConfig, CrmOutcomeEvent, Lead, Organization
from routers.lead_router import upsert_lead

GENESIS = "http://localhost:5000/api"
# 凭证不落库：从环境变量读取本地开发凭证（绝不提交真实 token）
TOKEN = os.environ["GENESIS_TEST_TOKEN"]
PROJECT = "6aa2360776ab59e92117bb18"

Base.metadata.create_all(bind=SHARED_ENGINE)
db = SharedSessionLocal()

org = Organization(name=f"e2ed-org-{time.time()}")
db.add(org); db.commit()
cfg = CrmIntegrationConfig(
    organization_id=org.id, base_url=GENESIS, project_id=PROJECT,
    service_token=TOKEN, enabled=True, last_health_status="ok",
)
db.add(cfg); db.commit()

print("== 1. 线索交接（dispatcher → Genesis）==")
lead = upsert_lead(db, org.id, {
    "email": f"waved.{int(time.time())}@example.com", "name": "WaveD Buyer",
    "company": "WaveD Co", "source": "Website AI Chat",
})
dispatcher.dispatch_once(db, worker_id="e2e-d")
link = db.query(CrmEntityLink).filter_by(lead_id=lead.id).one()
customer_id = link.remote_customer_id
print(f"   lead#{lead.id} → Genesis customer {customer_id}")

print("== 2. Genesis 侧把客户改为 won（模拟销售成交，走用户 API + JWT）==")
login = requests.post(f"{GENESIS}/auth/login", json={"username": "admin", "password": "123456"}, timeout=10)
assert login.status_code == 200, login.text
jwt = login.json()["data"]["token"]
upd = requests.put(
    f"{GENESIS}/customers/{customer_id}",
    json={"status": "won"},
    headers={"Authorization": f"Bearer {jwt}", "X-Project-Id": PROJECT},
    timeout=10,
)
assert upd.status_code == 200, upd.text
print("   Genesis 客户状态 → won")

print("== 3. AutoForceAI outcome 轮询（一个周期）==")
processed = poll_org_outcomes(db, cfg)
db.expire_all()
lead = db.query(Lead).filter_by(id=lead.id).one()
link = db.query(CrmEntityLink).filter_by(lead_id=lead.id).one()
ev = db.query(CrmOutcomeEvent).filter_by(organization_id=org.id).one()
print(f"   新事件 {processed} 个 → lead.status={lead.status}, link.remote_status={link.remote_status}")
print(f"   事件流水: {ev.event_id} {ev.from_status}→{ev.to_status}, cursor={cfg.outcome_cursor[:20]}…")
assert lead.status == "converted", "won 应把本地线索标记为 converted（成交归因）"
assert lead.source == "Website AI Chat", "获客来源不得被覆盖"
assert link.remote_status == "won"
assert ev.to_status == "won"

print("== 4. 幂等：再轮询一轮不重复归因 ==")
again = poll_org_outcomes(db, cfg)
assert again == 0
assert db.query(CrmOutcomeEvent).filter_by(organization_id=org.id).count() == 1
print("   重复轮询 0 新事件，无重复记录")

print("\nWAVE D E2E PASS")
db.close()
