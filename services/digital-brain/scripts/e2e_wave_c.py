"""Wave C 端到端验证：真实 dispatcher → 真实 Genesis Integration API。

用法：Genesis server 已在 :5000 运行后执行
    venv/Scripts/python -X utf8 scripts/e2e_wave_c.py
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "e2e.db").replace("\\", "/")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.models  # noqa: F401
from core.db_manager import SHARED_ENGINE, SharedSessionLocal
from core.crm import dispatcher
from core.crm.client import GenesisCRMClient
from database.base import Base
from database.shared_models import CrmEntityLink, CrmIntegrationConfig, CrmSyncJob, Lead, Organization
from routers.lead_router import upsert_lead

GENESIS = "http://localhost:5000/api"
TOKEN = os.environ["GENESIS_TEST_TOKEN"]  # local dev credential from env, never committed
PROJECT = "6aa2360776ab59e92117bb18"

Base.metadata.create_all(bind=SHARED_ENGINE)
db = SharedSessionLocal()

org = Organization(name=f"e2e-org-{datetime.now().timestamp()}")
db.add(org); db.commit()

cfg = CrmIntegrationConfig(
    organization_id=org.id, base_url=GENESIS, project_id=PROJECT,
    service_token=TOKEN, enabled=True,
)
db.add(cfg); db.commit()

print("== 1. 线索写入 → 同事务入队 ==")
lead = upsert_lead(db, org.id, {
    "email": "wavec.e2e@example.com", "name": "WaveC Buyer", "company": "WaveC Co",
    "country": "Germany", "products": "canvas tote bags",
    "intent_json": {"quantity": "3000 pcs", "target_price": "USD 1.10/pc", "summary": "Wave C 端到端验证线索"},
    "source": "Website AI Chat",
})
job = db.query(CrmSyncJob).filter_by(lead_id=lead.id).one()
print(f"   lead#{lead.id} → job#{job.id} pending, key={job.idempotency_key}")

print("== 2. 投递器真实投递 ==")
n = dispatcher.dispatch_once(db, worker_id="e2e")
db.refresh(job)
print(f"   处理 {n} 个 → job.status={job.status}")
assert job.status == "succeeded", job.last_error_summary
link = db.query(CrmEntityLink).filter_by(lead_id=lead.id).one()
print(f"   entity link: remote_customer_id={link.remote_customer_id}")

print("== 3. Genesis 侧确认客户真实存在（只读端点回查） ==")
client = GenesisCRMClient(GENESIS, TOKEN, PROJECT)
st = client.get_customer_status(f"lead:{lead.id}")
print(f"   Genesis customer: {st.customerId} status={st.status} name={st.name}")
assert st.customerId == link.remote_customer_id

print("== 4. 线索更新（载荷变化）→ 新 job → Genesis 返回 unchanged（同一客户） ==")
lead2 = upsert_lead(db, org.id, {"email": "wavec.e2e@example.com", "phone": "+49 30 777"})
assert lead2.id == lead.id  # 本地去重为同一线索
dispatcher.dispatch_once(db, worker_id="e2e")
jobs = db.query(CrmSyncJob).filter_by(lead_id=lead.id).order_by(CrmSyncJob.id).all()
print(f"   jobs={len(jobs)}, 状态={[j.status for j in jobs]}")
assert all(j.status == "succeeded" for j in jobs)
st2 = client.get_customer_status(f"lead:{lead.id}")
assert st2.customerId == link.remote_customer_id  # 仍是同一个客户，未重复创建
print(f"   Genesis 仍为同一客户 {st2.customerId}（无重复建档）")

print("== 5. 非法载荷 → 死信 ==")
bad = upsert_lead(db, org.id, {"name": "NoEmail Guy", "source": "manual"})
bad_job = db.query(CrmSyncJob).filter_by(lead_id=bad.id).one()
# 手工污染载荷模拟字段错误（email 非法）
bad_job.payload_json = {**bad_job.payload_json, "email": "not-an-email"}
db.commit()
dispatcher.dispatch_once(db, worker_id="e2e")
db.refresh(bad_job)
print(f"   job.status={bad_job.status}, code={bad_job.last_error_code}, http={bad_job.last_http_status}")
assert bad_job.status == "dead" and bad_job.last_error_code == "VALIDATION_ERROR"

print("== 6. 死信重投（修复载荷后） ==")
bad_job.payload_json = {k: v for k, v in bad_job.payload_json.items() if k != "email"}
bad_job.status = "pending"; bad_job.attempt_count = 0
bad_job.next_attempt_at = datetime.now() - timedelta(seconds=1); bad_job.dead_at = None
db.commit()
dispatcher.dispatch_once(db, worker_id="e2e")
db.refresh(bad_job)
print(f"   重投后 status={bad_job.status}")
assert bad_job.status == "succeeded"

print("== 7. 线索列表同步状态摘要 ==")
from routers.lead_router import _crm_status_map
m = _crm_status_map(db, org.id, [lead.id, bad.id])
print(f"   lead#{lead.id}: {m[lead.id]}")
print(f"   lead#{bad.id}: {m[bad.id]}")
assert m[lead.id]["synced"] and m[bad.id]["synced"]

print("\nWAVE C E2E PASS")
db.close()
