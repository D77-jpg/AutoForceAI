"""H-11: platform credentials never leave API responses or error details."""

from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from database.shared_models import SharedBase
from routers import platform_router


@pytest.fixture
def platform_api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SharedBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(platform_router.router)
    identity = {"id": 1, "role": "admin"}

    def database_override():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_shared_db] = database_override
    app.dependency_overrides[get_current_user] = lambda: identity
    with TestClient(app) as client:
        yield client, identity
    engine.dispose()


def test_provider_and_nested_model_never_return_credentials(platform_api):
    client, _ = platform_api
    secret = "provider-secret-should-not-leak"
    embedded = "https://user:password@example.invalid/v1?token=private"
    response = client.post("/api/v1/platform/providers", json={
        "name": "Provider", "api_key": secret, "base_url": embedded,
    })
    assert response.status_code == 200
    provider_id = response.json()["id"]
    assert secret not in response.text and embedded not in response.text
    response = client.post("/api/v1/platform/models", json={
        "provider_id": provider_id, "name": "test-model", "display_name": "Test",
        "api_key": "model-secret-should-not-leak", "base_url": embedded,
    })
    assert response.status_code == 200
    assert "model-secret-should-not-leak" not in response.text and embedded not in response.text
    for response in (client.get("/api/v1/platform/models"), client.get("/api/v1/platform/providers")):
        assert response.status_code == 200
        assert "api_key" not in response.text and "base_url" not in response.text
        assert secret not in response.text and embedded not in response.text
        assert "model-secret-should-not-leak" not in response.text


def test_blank_key_keeps_persisted_value_for_update_and_upsert(platform_api):
    client, _ = platform_api
    create = {"name": "stable", "display_name": "Original", "api_key": "stored-secret"}
    response = client.post("/api/v1/platform/models", json=create)
    assert response.status_code == 200
    model_id = response.json()["id"]
    assert client.put(f"/api/v1/platform/models/{model_id}", json={"display_name": "Edited", "api_key": ""}).status_code == 200
    assert client.post("/api/v1/platform/models", json={"name": "stable", "display_name": "Upserted"}).status_code == 200
    with platform_api_session(client) as db:
        from database.shared_models import LLMModel
        assert db.query(LLMModel).filter(LLMModel.id == model_id).first().api_key == "stored-secret"
    assert client.put(f"/api/v1/platform/models/{model_id}", json={"api_key": "replacement"}).status_code == 200
    with platform_api_session(client) as db:
        from database.shared_models import LLMModel
        assert db.query(LLMModel).filter(LLMModel.id == model_id).first().api_key == "replacement"


@contextmanager
def platform_api_session(client):
    """Reuse the FastAPI DB override so assertions inspect the persisted row."""
    yield from client.app.dependency_overrides[get_shared_db]()


def test_admin_required_for_management_but_authenticated_model_picker_works(platform_api):
    client, identity = platform_api
    identity["role"] = "user"
    assert client.get("/api/v1/platform/models?geo_only=true").status_code == 200
    assert client.get("/api/v1/platform/providers").status_code == 403
    assert client.post("/api/v1/platform/providers", json={"name": "Blocked"}).status_code == 403
    assert client.post("/api/v1/platform/models", json={"name": "blocked", "display_name": "Blocked"}).status_code == 403
    assert client.put("/api/v1/platform/models/1", json={"api_key": "blocked"}).status_code == 403
    assert client.delete("/api/v1/platform/models/1").status_code == 403


def test_anonymous_model_list_is_denied(platform_api):
    client, _ = platform_api
    client.app.dependency_overrides.pop(get_current_user)
    assert client.get("/api/v1/platform/models").status_code == 401
    assert client.get("/api/v1/platform/providers").status_code == 401


def test_database_error_never_includes_secret(platform_api):
    client, _ = platform_api
    class BrokenSession:
        def query(self, model):
            return self
        def filter(self, *args):
            return self
        def first(self):
            return None
        def add(self, model):
            pass
        def commit(self):
            raise ValueError("database parameters include private-secret")
        def rollback(self):
            pass

    app = client.app
    app.dependency_overrides[get_shared_db] = lambda: BrokenSession()
    response = client.post("/api/v1/platform/models", json={
        "name": "broken", "display_name": "Broken", "api_key": "private-secret",
    })
    assert response.status_code == 400
    assert "private-secret" not in response.text
    assert "parameters" not in response.text
