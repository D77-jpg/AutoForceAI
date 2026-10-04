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
from database.shared_models import Organization, User, LLMModel, LLMRequestLog, BrainMessage, KnowledgeBase, KnowledgeDoc, KnowledgeChunk
from database.models import MarketingContent
from routers import agent_router, brain_router, platform_router, auth_router, kb_router, marketing_router


@pytest.fixture
def env(monkeypatch):
    for key in ('OPENAI_API_KEY', 'DASHSCOPE_API_KEY', 'ZHIPUAI_API_KEY', 'DEEPSEEK_API_KEY'):
        monkeypatch.setenv(key, '')
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
    for router in (agent_router.router, brain_router.router, platform_router.router, auth_router.router, kb_router.router, marketing_router.router):
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


def test_explicit_kb_search_and_mutations_enforce_organization(env):
    client, factory, identity = env
    own = client.post('/api/v1/kb/bases', json={'name': 'owned'}).json()['id']
    with factory() as db:
        foreign = KnowledgeBase(name='private', organization_id=2)
        shared = KnowledgeBase(name='shared', organization_id=None)
        db.add_all([foreign, shared])
        db.commit()
        foreign_id, shared_id = foreign.id, shared.id
    assert client.post('/api/v1/kb/search', json={'query': 'facts', 'kb_ids': [foreign_id]}).status_code == 403
    assert client.get(f'/api/v1/kb/bases/{foreign_id}/docs').status_code == 403
    assert client.patch(f'/api/v1/kb/bases/{shared_id}', json={'name': 'hijacked'}).status_code == 403
    assert client.delete(f'/api/v1/kb/bases/{shared_id}').status_code == 403
    assert client.post(f'/api/v1/kb/bases/{shared_id}/docs', files={'file': ('x.txt', b'facts')}).status_code == 403
    assert client.patch(f'/api/v1/kb/bases/{own}', json={'name': 'saved'}).status_code == 200
    assert any(k['name'] == 'saved' for k in client.get('/api/v1/kb/bases').json()['items'])
    with factory() as db:
        db.get(User, 1).organization_id = None
        db.commit()
    for path in ('/api/v1/kb/bases', '/api/v1/kb/config'):
        assert client.get(path).status_code == 403
    assert client.post('/api/v1/kb/search', json={'query': 'facts', 'kb_ids': [foreign_id]}).status_code == 403
    assert client.post('/api/v1/kb/bases', json={'name': 'rogue'}).status_code == 403


def test_upload_filename_is_normalized_and_library_deletion_cleans_files(env, monkeypatch, tmp_path):
    client, factory, _ = env
    monkeypatch.setattr(kb_router, 'UPLOAD_ROOT', str(tmp_path))
    monkeypatch.setattr(kb_router, '_run_index', lambda *args: None)
    kb = client.post('/api/v1/kb/bases', json={'name': 'owned'}).json()['id']
    response = client.post(f'/api/v1/kb/bases/{kb}/docs', files={'file': ('../../folder/facts.txt', b'Public facts')})
    assert response.status_code == 200 and response.json()['filename'] == 'facts.txt'
    with factory() as db:
        doc = db.query(KnowledgeDoc).one()
        from pathlib import Path
        path = Path(doc.file_path)
        assert path.resolve().is_relative_to(tmp_path.resolve()) and path.is_file()
    assert client.delete(f'/api/v1/kb/bases/{kb}').status_code == 200
    assert not path.exists()
    with factory() as db:
        assert db.query(KnowledgeDoc).count() == 0


@pytest.mark.parametrize('result', ['', 'too short', '{"body": ["invalid"]}'])
def test_invalid_model_output_never_becomes_template_success(env, monkeypatch, result):
    client, factory, _ = env
    monkeypatch.setattr(marketing_router, 'query_default_llm', lambda *args, **kwargs: result)
    response = client.post('/api/v1/marketing/text/generate', json={'content_type': 'outreach_email', 'product_name': 'fictional'})
    assert response.status_code == 502
    with factory() as db:
        assert db.query(MarketingContent).count() == 0


def test_provider_exception_is_sanitized_and_missing_image_key_is_not_success(env, monkeypatch):
    client, factory, _ = env
    def failed(*args, **kwargs):
        raise RuntimeError('secret-key in provider response')
    monkeypatch.setattr(marketing_router, 'query_default_llm', failed)
    response = client.post('/api/v1/marketing/text/generate', json={'content_type': 'outreach_email', 'product_name': 'fictional'})
    assert response.status_code == 502 and 'secret-key' not in response.text
    assert client.post('/api/v1/marketing/images/generate', json={'prompt': 'cube'}).status_code == 503
    with factory() as db:
        assert db.query(MarketingContent).count() == 0


def test_saved_image_file_is_durable_and_owner_scoped(env, monkeypatch, tmp_path):
    client, factory, identity = env
    path = tmp_path / ('a' * 32 + '.png')
    path.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
    monkeypatch.setattr(marketing_router, 'IMAGE_ROOT', tmp_path)
    monkeypatch.setattr(marketing_router, 'generate_image_url', lambda *args: 'https://fixture.aliyuncs.com/image.png')
    monkeypatch.setattr(marketing_router, 'store_image', lambda *args: path)
    response = client.post('/api/v1/marketing/images/generate', json={'prompt': 'cube'})
    assert response.status_code == 200 and response.json()['mock'] is False
    url = response.json()['url']
    assert client.get(url).content == path.read_bytes()
    assert client.get('/api/v1/marketing/images').json()['items'][0]['image_url'] == url
    identity['id'] = 2
    assert client.get(url).status_code == 404
    assert client.get('/api/v1/marketing/images').json()['items'] == []


def test_text_edits_persist_with_subject_word_count_and_owner_scope(env):
    client, factory, identity = env
    with factory() as db:
        record = MarketingContent(user_id=1, content_type='outreach_email', title='Original', body='Original body', extra={'subject': 'Email subject', 'mock': False})
        db.add(record)
        db.commit()
        content_id = record.id
    response = client.patch(f'/api/v1/marketing/text/{content_id}', json={'title': 'Saved title', 'body': 'Saved real edited body'})
    assert response.status_code == 200
    restored = client.get(f'/api/v1/marketing/text/{content_id}').json()
    assert restored['title'] == 'Saved title' and restored['body'] == 'Saved real edited body'
    assert restored['subject'] == 'Email subject' and restored['word_count'] == 4
    assert client.patch(f'/api/v1/marketing/text/{content_id}', json={'title': ' ', 'body': 'empty title'}).status_code == 422
    identity['id'] = 2
    assert client.patch(f'/api/v1/marketing/text/{content_id}', json={'title': 'hijacked', 'body': 'private'}).status_code == 404


def test_unconfigured_or_unconnected_publish_never_creates_success_job(env, monkeypatch):
    from database.models import RPAJob
    client, factory, _ = env
    monkeypatch.setattr(marketing_router, 'wp_publish', lambda *args, **kwargs: {'mode': 'dry_run', 'msg': 'unconfigured'})
    for platform in ('website', 'wordpress'):
        assert client.post('/api/v1/marketing/publish', json={'platform': platform, 'title': 'public test', 'content': 'public text'}).status_code == 503
    with factory() as db:
        assert db.query(RPAJob).count() == 0
