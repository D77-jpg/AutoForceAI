"""Truthful completion and tenant-scoped setup for local acceptance."""
import json
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.dependencies import get_current_user, get_current_user_id, get_db
from core.db_manager import get_shared_db
from database.base import Base
from database.models import Project
from database.shared_models import Organization, User, LLMModel, LLMRequestLog, BrainMessage
from routers import agent_router, brain_router, platform_router, auth_router


@pytest.fixture
def env(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add_all([Organization(id=1, name='acceptance'), Organization(id=2, name='other')])
        db.flush()
        db.add_all([User(id=1, username='owner', organization_id=1, is_active=True),
                    User(id=2, username='other', organization_id=2, is_active=True)])
        db.add(LLMModel(name='test-llm', display_name='Test', type='LLM', is_active=True, is_default=True, api_key='private-key'))
        db.commit()
    app = FastAPI()
    for router in (agent_router.router, brain_router.router, platform_router.router, auth_router.router):
        app.include_router(router)
    identity = {'id': 1, 'role': 'admin'}
    def database():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_shared_db] = database
    app.dependency_overrides[get_current_user_id] = lambda: identity['id']
    app.dependency_overrides[get_current_user] = lambda: identity
    monkeypatch.setattr(brain_router, 'SharedSessionLocal', factory)
    with TestClient(app) as client:
        yield client, factory, identity
    engine.dispose()


def test_organization_creation_returns_real_refreshed_token(env):
    from core.auth import decode_token
    client, factory, _ = env
    with factory() as db:
        db.get(User, 1).organization_id = None
        db.commit()
    response = client.post('/auth/organization/create', json={'name': 'new-organization'})
    assert response.status_code == 200
    data = response.json()
    payload = decode_token(data['access_token'])
    assert payload['org_id'] == data['organization_id']
    assert payload['role'] == 'enterprise_admin'


def test_project_creation_is_persistent_and_owner_scoped(env):
    client, factory, identity = env
    response = client.post('/agents/projects', json={'name': '  Real project  '})
    assert response.status_code == 201
    project_id = response.json()['id']
    assert response.json()['organization_id'] == 1
    with factory() as db:
        project = db.get(Project, project_id)
        assert project.user_id == 1 and project.name == 'Real project'
    assert client.get('/agents/projects').json()[0]['id'] == project_id
    employee = client.post(f'/agents/{project_id}/employees/from-template', json={'template_key': 'lead_researcher'})
    assert employee.status_code == 200
    identity['id'] = 2
    assert client.get('/agents/projects').json() == []
    assert client.get(f'/agents/{project_id}/employees').status_code == 404
    assert client.post('/agents/projects', json={'name': '   '}).status_code == 422
    assert client.post('/agents/projects', json={'name': 'x', 'user_id': 1}).status_code == 422


def test_platform_overview_is_observed_not_invented_and_admin_only(env):
    client, factory, identity = env
    empty = client.get('/api/v1/platform/overview').json()
    assert empty['requests_today'] == 0 and empty['average_latency_ms'] is None
    assert empty['success_rate'] is None and empty['active_models'] == 1
    now = datetime.now()
    with factory() as db:
        db.add_all([LLMRequestLog(model='m', status='success', latency_ms=200, created_at=now),
                    LLMRequestLog(model='m', status='success', latency_ms=400, created_at=now),
                    LLMRequestLog(model='m', status='error', latency_ms=1000, created_at=now),
                    LLMRequestLog(model='m', status='success', latency_ms=9999, created_at=now - timedelta(days=2))])
        db.commit()
    response = client.get('/api/v1/platform/overview')
    data = response.json()
    assert data['requests_today'] == 3 and data['average_latency_ms'] == 300
    assert data['successful_requests_today'] == 2 and data['failed_requests_today'] == 1
    assert data['success_rate'] == 66.7
    assert 'private-key' not in response.text and 'api_key' not in response.text
    identity['role'] = 'user'
    assert client.get('/api/v1/platform/overview').status_code == 403


def test_capabilities_report_configuration_without_secrets_or_health_claims(env, monkeypatch):
    client, _, identity = env
    monkeypatch.setenv('SERPER_API_KEY', 'secret-search-key')
    monkeypatch.setenv('DASHSCOPE_API_KEY', '')
    response = client.get('/api/v1/platform/capabilities')
    data = response.json()
    items = {item['id']: item for item in data['items']}
    assert items['web_search']['configured'] is True
    assert items['image_generation']['configured'] is False
    assert data['verified'] is False
    assert 'secret-search-key' not in response.text
    identity['role'] = 'user'
    assert client.get('/api/v1/platform/capabilities').status_code == 403


@pytest.mark.parametrize('failure', ['provider', 'empty', 'persistence'])
def test_brain_never_reports_done_for_failed_or_unsaved_answer(env, monkeypatch, failure):
    client, factory, _ = env
    class Provider:
        def chat_stream(self, *args, **kwargs):
            if failure == 'provider':
                yield 'partial'
                raise RuntimeError('private-key must not leak')
            if failure == 'persistence':
                yield 'valid answer'
            else:
                yield ''
    monkeypatch.setattr(brain_router.ModelFactory, 'get_provider', lambda *args, **kwargs: Provider())
    if failure == 'persistence':
        calls = {'count': 0}
        def broken_save_factory():
            calls['count'] += 1
            db = factory()
            if calls['count'] == 2:
                def fail_commit():
                    raise RuntimeError('driver parameters private-key')
                db.commit = fail_commit
            return db
        monkeypatch.setattr(brain_router, 'SharedSessionLocal', broken_save_factory)
    response = client.post('/api/v1/brain/chat', json={'query': 'test'})
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1]['t'] == 'error'
    assert not any(event['t'] == 'done' for event in events)
    assert 'private-key' not in response.text
    with factory() as db:
        assert db.query(BrainMessage).filter_by(role='assistant').count() == 0


def test_brain_answer_and_history_survive_new_database_session(env, monkeypatch):
    client, factory, identity = env
    class Provider:
        def chat_stream(self, *args, **kwargs):
            yield {'type': 'content', 'content': '真实'}
            yield {'type': 'content', 'content': '回答'}
    monkeypatch.setattr(brain_router.ModelFactory, 'get_provider', lambda *args, **kwargs: Provider())
    response = client.post('/api/v1/brain/chat', json={'query': 'test'})
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1]['t'] == 'done'
    session_id = events[0]['session_id']
    with factory() as db:
        assert db.query(BrainMessage).filter_by(role='assistant').one().content == '真实回答'
    history = client.get(f'/api/v1/brain/sessions/{session_id}/messages').json()
    assert history[-1]['content'] == '真实回答'
    identity['id'] = 2
    assert client.get(f'/api/v1/brain/sessions/{session_id}/messages').status_code == 404
