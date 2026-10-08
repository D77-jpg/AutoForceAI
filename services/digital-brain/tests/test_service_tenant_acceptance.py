"""HTTP/JWT checks for customer-service data boundaries in a disposable database."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core import dependencies
from core.auth import create_access_token
from core.db_manager import get_shared_db
from database.base import Base
from database.models import ChatMessage, ChatSession
from database.shared_models import Bot, KnowledgeBase, Lead, Organization, QualityRule, User
from routers import service_chat_router as service


@pytest.fixture
def customer_service(monkeypatch):
    monkeypatch.setenv('JWT_SECRET', 'isolated-service-acceptance-key-with-adequate-length')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(dependencies, 'SharedSessionLocal', factory)
    monkeypatch.setattr(dependencies, 'enforce_user_rate_limit', lambda request: None)
    with factory() as db:
        db.add_all([Organization(id=1, name='Synthetic A'), Organization(id=2, name='Synthetic B')])
        db.flush()
        db.add_all([
            User(id=1, username='service-a', organization_id=1, role='enterprise_admin'),
            User(id=2, username='service-b', organization_id=2, role='enterprise_admin'),
            User(id=3, username='service-unassigned', role='user'),
        ])
        db.add_all([
            KnowledgeBase(id=1, name='A catalog', organization_id=1),
            KnowledgeBase(id=2, name='B catalog', organization_id=2, is_public=True),
            KnowledgeBase(id=3, name='Shared public', is_public=True),
            KnowledgeBase(id=4, name='Shared private', is_public=False),
        ])
        db.flush()
        db.add_all([
            Bot(id=1, name='Bot A', organization_id=1, kb_id=1, is_active=True),
            Bot(id=2, name='Bot B', organization_id=2, kb_id=2, is_active=False),
        ])
        db.flush()
        db.add_all([
            ChatSession(id=1, session_uuid='synthetic-a', bot_id=1, status='active'),
            ChatSession(id=2, session_uuid='synthetic-b', bot_id=2, status='closed'),
            ChatSession(id=3, session_uuid='synthetic-orphan', status='active'),
            Lead(id=1, organization_id=1, email='a@example.invalid'),
            Lead(id=2, organization_id=2, email='b@example.invalid'),
            QualityRule(id=1, name='Rule A', organization_id=1),
            QualityRule(id=2, name='Rule B', organization_id=2),
            QualityRule(id=3, name='Shared rule'),
        ])
        db.flush()
        db.add_all([
            ChatMessage(session_id=1, role='user', content='Synthetic A conversation'),
            ChatMessage(session_id=2, role='user', content='Synthetic B conversation'),
        ])
        db.commit()
    app = FastAPI()
    app.include_router(service.router)

    def database():
        with factory() as db:
            yield db
    app.dependency_overrides[get_shared_db] = database
    headers = {i: {'Authorization': 'Bearer ' + create_access_token({'id': i})} for i in (1, 2, 3)}
    with TestClient(app) as client:
        yield client, factory, headers
    engine.dispose()


def test_session_details_lists_stats_and_rules_are_tenant_scoped(customer_service):
    client, _, headers = customer_service
    prefix = '/api/v1/service'
    for user, own, other in [(1, 'synthetic-a', 'synthetic-b'), (2, 'synthetic-b', 'synthetic-a')]:
        listing = client.get(prefix + '/sessions', headers=headers[user])
        assert listing.status_code == 200
        assert [s['session_uuid'] for s in listing.json()['items']] == [own]
        detail = client.get(prefix + '/sessions/' + own, headers=headers[user])
        assert detail.status_code == 200 and detail.json()['messages'][0]['content'].startswith('Synthetic')
        assert client.get(prefix + '/sessions/' + other, headers=headers[user]).status_code == 404
        assert client.get(prefix + '/sessions/synthetic-orphan', headers=headers[user]).status_code == 404
        stats = client.get(prefix + '/stats', headers=headers[user]).json()
        assert stats == {'sessions': 1, 'active': int(user == 1), 'leads': 1}
        assert {r['id'] for r in client.get(prefix + '/rules', headers=headers[user]).json()['items']} == {user, 3}
        assert [b['id'] for b in client.get(prefix + '/bots', headers=headers[user]).json()['items']] == [user]


@pytest.mark.parametrize('path', ['bots', 'sessions', 'sessions/synthetic-a', 'rules', 'stats'])
def test_anonymous_and_unassigned_users_cannot_read_management(customer_service, path):
    client, _, headers = customer_service
    url = '/api/v1/service/' + path
    assert client.get(url).status_code == 401
    assert client.get(url, headers=headers[3]).status_code == 403


def test_bot_creation_update_and_binding_cannot_cross_organizations(customer_service):
    client, factory, headers = customer_service
    prefix = '/api/v1/service/bots'
    for kb_id in (2, 4, 999):
        invalid = {'name': 'Invalid binding', 'kb_id': kb_id}
        assert client.post(prefix, json=invalid, headers=headers[1]).status_code == 404
        assert client.patch(prefix + '/1', json=invalid, headers=headers[1]).status_code == 404
    assert client.patch(prefix + '/2', json={'name': 'Wrong tenant'}, headers=headers[1]).status_code == 404
    assert client.patch(prefix + '/1', json={'name': 'Unassigned'}, headers=headers[3]).status_code == 403
    assert client.post(prefix, json={'name': 'Unassigned'}, headers=headers[3]).status_code == 403
    assert client.post('/api/v1/service/rules', json={'name': 'Unassigned'}, headers=headers[3]).status_code == 403
    with factory() as db:
        assert db.query(Bot).count() == 2
        assert (db.get(Bot, 1).name, db.get(Bot, 1).kb_id) == ('Bot A', 1)
    for kb_id in (1, 3, None):
        response = client.post(prefix, json={'name': 'Valid binding', 'kb_id': kb_id}, headers=headers[1])
        assert response.status_code == 200
        with factory() as db:
            bot = db.get(Bot, response.json()['id'])
            assert bot.organization_id == 1 and bot.kb_id == kb_id


def test_widget_requires_explicit_active_bot_and_does_not_mutate_invalid_sessions(customer_service, monkeypatch):
    client, factory, _ = customer_service
    monkeypatch.setattr(service, '_reply_with_kb', lambda *args: pytest.fail('Invalid bot must not call a model'))
    for body in ({}, {'bot_id': 2}, {'bot_id': 999}):
        assert client.post('/api/v1/service/widget/start', json=body).status_code == 404
    invalid = client.post('/api/v1/service/widget/chat', json={
        'session_uuid': 'synthetic-b', 'message': 'Invalid chat', 'visitor_email': 'changed@example.invalid',
    })
    assert invalid.status_code == 404
    with factory() as db:
        assert db.query(ChatSession).count() == 3
        assert db.get(ChatSession, 2).visitor_email is None
        assert db.query(ChatMessage).count() == 2
        db.get(Bot, 1).kb_id = 2  # Simulate a legacy foreign binding.
        db.commit()
    assert client.post('/api/v1/service/widget/start', json={'bot_id': 1}).status_code == 404
    assert client.post('/api/v1/service/widget/chat', json={
        'session_uuid': 'synthetic-a', 'message': 'Invalid binding',
    }).status_code == 404
    with factory() as db:
        assert db.query(ChatMessage).count() == 2


def test_widget_welcome_history_and_retrieval_use_only_bound_knowledge(customer_service, monkeypatch):
    client, factory, _ = customer_service
    start = client.post('/api/v1/service/widget/start', json={'bot_id': 1})
    assert start.status_code == 200 and start.json()['bot_id'] == 1
    history = client.get('/api/v1/service/widget/history/' + start.json()['session_uuid'])
    assert history.status_code == 200 and len(history.json()['messages']) == 1
    queried = []
    monkeypatch.setattr(service.KnowledgeRetriever, 'search_multi_kb', lambda self, kb_ids, *a, **kw: queried.append(kb_ids) or [])
    monkeypatch.setattr(service, 'get_default_llm_model', lambda db: None)
    with factory() as db:
        service._reply_with_kb(db, db.get(Bot, 1), 'MOQ?')
        assert queried == [[1]]
        queried.clear()
        db.get(Bot, 1).kb_id = None
        db.commit()
        service._reply_with_kb(db, db.get(Bot, 1), 'MOQ?')
        assert queried == []  # No fallback to other companies' public catalogs.
