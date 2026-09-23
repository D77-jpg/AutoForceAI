"""阶段 2.9 P0-1：service token 加密存储与旧明文迁移。

运行（services/digital-brain 目录）：
    venv/Scripts/python -m pytest tests/test_crm_credentials.py -q

覆盖：密文落库、正确解密、错误密钥、损坏密文、缺密钥、旧明文一次性迁移、
前端只拿到 has_token/token_preview、dispatcher 在解密失败时暂停该组织投递。
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import database.models  # noqa: E402,F401
from core import credentials  # noqa: E402
from core.credentials import (  # noqa: E402
    ERR_DECRYPT_FAILED,
    ERR_INVALID_KEY,
    ERR_MISSING_KEY,
    CredentialError,
    decrypt_secret,
    encrypt_secret,
    is_encrypted,
)
from core.db_manager import SHARED_ENGINE, SharedSessionLocal  # noqa: E402
from core.crm import dispatcher  # noqa: E402
from database.base import Base  # noqa: E402
from database.shared_models import (  # noqa: E402
    CrmIntegrationConfig,
    CrmSyncJob,
    Organization,
    User,
    UserRole,
)
import routers.crm_integration_router as crm_router  # noqa: E402
from routers.lead_router import upsert_lead  # noqa: E402

PLAIN_TOKEN = "gci_aaaabbbbccccddddeeeeffff00001111"


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setenv(credentials.ENV_KEY, Fernet.generate_key().decode())


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
def org(db):
    o = Organization(name=f"org-{datetime.now().timestamp()}")
    db.add(o)
    db.commit()
    return o


# ---------------------------------------------------------------- 加解密原语

def test_encrypt_decrypt_roundtrip():
    stored = encrypt_secret(PLAIN_TOKEN)
    assert stored.startswith("enc:v1:")
    assert PLAIN_TOKEN not in stored
    assert decrypt_secret(stored) == PLAIN_TOKEN


def test_fernet_key_form():
    from cryptography.fernet import Fernet
    import os
    fernet_key = Fernet.generate_key().decode()
    old = os.environ[credentials.ENV_KEY]
    os.environ[credentials.ENV_KEY] = fernet_key
    try:
        stored = encrypt_secret(PLAIN_TOKEN)
        assert decrypt_secret(stored) == PLAIN_TOKEN
    finally:
        os.environ[credentials.ENV_KEY] = old


def test_plain_passphrase_is_rejected(monkeypatch):
    monkeypatch.setenv(credentials.ENV_KEY, "short-human-passphrase")
    with pytest.raises(CredentialError) as exc:
        encrypt_secret(PLAIN_TOKEN)
    assert exc.value.code == ERR_INVALID_KEY
    assert "short-human-passphrase" not in str(exc.value)


def test_wrong_key_fails_without_leaking(monkeypatch):
    from cryptography.fernet import Fernet
    stored = encrypt_secret(PLAIN_TOKEN)
    monkeypatch.setenv(credentials.ENV_KEY, Fernet.generate_key().decode())
    with pytest.raises(CredentialError) as exc:
        decrypt_secret(stored)
    assert exc.value.code == ERR_DECRYPT_FAILED
    assert PLAIN_TOKEN not in str(exc.value)
    assert stored not in str(exc.value)


def test_corrupted_ciphertext_fails():
    stored = encrypt_secret(PLAIN_TOKEN)
    corrupted = stored[:-8] + "AAAAAA=="
    with pytest.raises(CredentialError) as exc:
        decrypt_secret(corrupted)
    assert exc.value.code == ERR_DECRYPT_FAILED


def test_ciphertext_without_key_is_hard_error(monkeypatch):
    stored = encrypt_secret(PLAIN_TOKEN)
    monkeypatch.delenv(credentials.ENV_KEY, raising=False)
    with pytest.raises(CredentialError) as exc:
        decrypt_secret(stored)
    assert exc.value.code == ERR_MISSING_KEY


# ---------------------------------------------------------------- 模型与迁移

def test_model_store_ciphertext_and_preview_from_last4(db, org):
    cfg = CrmIntegrationConfig(
        organization_id=org.id, base_url="http://localhost:5000/api",
        project_id="p1",
    )
    cfg.set_service_token(PLAIN_TOKEN)
    db.add(cfg)
    db.commit()

    row = db.query(CrmIntegrationConfig).filter_by(organization_id=org.id).one()
    assert is_encrypted(row.service_token)
    assert PLAIN_TOKEN not in row.service_token       # 密文落库
    assert row.token_last4 == PLAIN_TOKEN[-4:]
    assert row.token_preview == "****1111"             # 预览不依赖解密
    assert row.get_service_token() == PLAIN_TOKEN      # 服务端可正确解密


def test_legacy_plaintext_migrates_on_read_write(db, org):
    # 直接写明文模拟阶段 2.9 之前的旧记录
    cfg = CrmIntegrationConfig(
        organization_id=org.id, base_url="http://localhost:5000/api",
        project_id="p1", service_token=PLAIN_TOKEN,
    )
    db.add(cfg)
    db.commit()

    cfg = db.query(CrmIntegrationConfig).filter_by(organization_id=org.id).one()
    assert cfg.get_service_token() == PLAIN_TOKEN      # 旧明文仍可读（迁移前兼容）
    assert cfg.migrate_token_if_legacy() is True
    db.commit()

    cfg = db.query(CrmIntegrationConfig).filter_by(organization_id=org.id).one()
    assert is_encrypted(cfg.service_token)
    assert cfg.token_last4 == PLAIN_TOKEN[-4:]
    assert cfg.get_service_token() == PLAIN_TOKEN
    assert cfg.migrate_token_if_legacy() is False      # 不重复迁移


def test_legacy_migration_requires_key(db, org, monkeypatch):
    cfg = CrmIntegrationConfig(
        organization_id=org.id, base_url="http://localhost:5000/api",
        project_id="p1", service_token=PLAIN_TOKEN,
    )
    db.add(cfg)
    db.commit()
    monkeypatch.delenv(credentials.ENV_KEY, raising=False)
    cfg = db.query(CrmIntegrationConfig).filter_by(organization_id=org.id).one()
    with pytest.raises(CredentialError) as exc:
        cfg.migrate_token_if_legacy()
    assert exc.value.code == ERR_MISSING_KEY
    assert cfg.service_token == PLAIN_TOKEN  # 迁移失败不留半成品


def test_connection_failure_commit_preserves_legacy_plaintext(db, org, monkeypatch):
    """完整回归：/test 捕获迁移错误后会 commit health，但不得把旧 token 提交为 NULL。"""
    admin = User(
        username=f"cred-admin-{org.id}", email=f"cred-{org.id}@example.com",
        hashed_password="x", role=UserRole.ENTERPRISE_ADMIN.value,
        organization_id=org.id,
    )
    cfg = CrmIntegrationConfig(
        organization_id=org.id, base_url="http://localhost:5000/api",
        project_id="p1", service_token=PLAIN_TOKEN,
    )
    db.add_all([admin, cfg])
    db.commit()
    monkeypatch.delenv(credentials.ENV_KEY, raising=False)

    result = crm_router.test_connection({"id": admin.id}, db)
    assert result.ok is False
    assert ERR_MISSING_KEY in result.detail

    org_id = org.id
    db.close()
    verify = SharedSessionLocal()
    try:
        persisted = verify.query(CrmIntegrationConfig).filter_by(organization_id=org_id).one()
        assert persisted.service_token == PLAIN_TOKEN
        assert persisted.last_health_status == "error"
    finally:
        verify.close()


# ---------------------------------------------------------------- 运行链路

def test_dispatcher_pauses_on_decrypt_failure(db, org, monkeypatch):
    from cryptography.fernet import Fernet
    cfg = CrmIntegrationConfig(
        organization_id=org.id, base_url="http://localhost:5000/api",
        project_id="p1", enabled=True,
    )
    cfg.set_service_token(PLAIN_TOKEN)
    db.add(cfg)
    db.commit()

    lead = upsert_lead(db, org.id, {"email": "pause@x.com"})
    # 换密钥 → 解密失败
    monkeypatch.setenv(credentials.ENV_KEY, Fernet.generate_key().decode())
    dispatcher.dispatch_once(db, worker_id="w-cred")

    job = db.query(CrmSyncJob).filter_by(lead_id=lead.id).one()
    db.refresh(cfg)
    assert job.status == "retrying"
    assert job.last_error_code == ERR_DECRYPT_FAILED
    assert cfg.last_health_status == "credential_error"
    assert "已暂停" in cfg.last_health_detail or "凭证不可用" in cfg.last_health_detail

    # 暂停期间到期也不再发起 HTTP（无 client 可建）
    job.next_attempt_at = datetime.now() - timedelta(seconds=1)
    db.commit()
    dispatcher.dispatch_once(db, worker_id="w-cred")
    job = db.query(CrmSyncJob).filter_by(lead_id=lead.id).one()
    assert job.status == "retrying"
