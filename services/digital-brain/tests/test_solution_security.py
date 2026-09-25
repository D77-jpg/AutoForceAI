"""H-02 contract: organization isolation, honest generation, and safe PPT export."""
import io
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pptx import Presentation

from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from database.shared_models import SharedBase, Organization, User, KnowledgeBase, KnowledgeDoc, KnowledgeChunk
from routers import solution_router as solution


@pytest.fixture
def fixture_app():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SharedBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)
    with session() as db:
        db.add_all([Organization(id=1, name='Our Org'), Organization(id=2, name='Other Org')])
        db.add_all([User(id=1, username='member', organization_id=1), User(id=2, username='other', organization_id=2), User(id=3, username='orphan')])
        db.add_all([KnowledgeBase(id=11, name='Own KB', organization_id=1), KnowledgeBase(id=22, name='Secret KB', organization_id=2), KnowledgeBase(id=33, name='Shared legacy KB')])
        db.add(KnowledgeDoc(id=101, kb_id=11, filename='Own source', status='indexed', chunk_count=1))
        db.add(KnowledgeChunk(id=201, doc_id=101, chunk_index=0, chunk_text='Product: sample lead time ten days.'))
        db.commit()
    app = FastAPI()
    app.include_router(solution.router)
    identity = {'id': 1}

    def db_override():
        with session() as db:
            yield db

    app.dependency_overrides[get_shared_db] = db_override
    app.dependency_overrides[get_current_user] = lambda: identity
    with TestClient(app) as client:
        yield client, identity
    engine.dispose()


def test_kb_picker_is_only_own_organization(fixture_app):
    client, identity = fixture_app
    r = client.get('/api/v1/solution/knowledge-bases')
    assert r.status_code == 200
    assert [item['id'] for item in r.json()['items']] == [11]
    identity['id'] = 3
    assert client.get('/api/v1/solution/knowledge-bases').status_code == 403
    identity['id'] = 2
    assert [item['id'] for item in client.get('/api/v1/solution/knowledge-bases').json()['items']] == [22]


@pytest.mark.parametrize('path,payload', [
    ('context', {'topic': 'sample', 'kb_ids': [22]}),
    ('outline', {'topic': 'sample', 'kb_ids': [22], 'context_override': 'forged source'}),
    ('page/content', {'topic': 'sample', 'kb_ids': [22], 'page_title': 'page'}),
    ('context', {'topic': 'sample', 'kb_ids': [999]}),
    ('context', {'topic': 'sample', 'kb_ids': [33]}),
])
def test_foreign_and_unknown_kb_ids_denied(fixture_app, path, payload):
    client, _ = fixture_app
    assert client.post('/api/v1/solution/' + path, json=payload).status_code == 403


@pytest.mark.parametrize('bad_id', ['22', 0, -1, 1.5, True])
def test_malformed_kb_id_rejected(fixture_app, bad_id):
    client, _ = fixture_app
    assert client.post('/api/v1/solution/context', json={'topic': 'sample', 'kb_ids': [bad_id]}).status_code == 422


def test_empty_kb_and_no_model_are_honest(fixture_app):
    client, _ = fixture_app
    with patch.object(solution, 'QwenClient') as qwen, patch.object(solution.KnowledgeRetriever, 'search_multi_kb', return_value=[]):
        qwen.return_value.api_key = None
        result = client.post('/api/v1/solution/context', json={'topic': 'sample', 'kb_ids': [11]})
        assert result.status_code == 200
        assert result.json()['items'] == []
        assert [log['step'] for log in result.json()['logs']] == ['Scope Validation', 'Retrieval Completed']
        outline = client.post('/api/v1/solution/outline', json={'topic': 'sample', 'kb_ids': [11]}).json()
        page = client.post('/api/v1/solution/page/content', json={'topic': 'sample', 'kb_ids': [11], 'page_title': 'intro'}).json()
    for value in [outline, page]:
        assert value['generation_mode'] == 'fallback'
        assert value['fallback_reason'] == 'model_not_configured'
        assert value['knowledge_used'] is False
        assert value['sources'] == []
    assert len(outline['pages']) > 0
    assert page['bullets'] == []  # Never export template claims as generated facts.


def test_model_failures_never_claim_success(fixture_app):
    client, _ = fixture_app
    from types import SimpleNamespace
    response = SimpleNamespace(status_code=200, output=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"reasoning":"Qwen API Error: leaked"}'))]))
    with patch.object(solution, 'QwenClient') as qwen, patch('dashscope.Generation.call', return_value=response), patch.object(solution.KnowledgeRetriever, 'search_multi_kb', return_value=[]):
        qwen.return_value.api_key = 'test-key'
        outline = client.post('/api/v1/solution/outline', json={'topic': 'sample'}).json()
        page = client.post('/api/v1/solution/page/content', json={'topic': 'sample', 'page_title': 'intro'}).json()
    assert outline['generation_mode'] == page['generation_mode'] == 'fallback'
    assert 'leaked' not in str(outline) and 'leaked' not in str(page)


def test_configured_model_reports_real_generation_and_only_real_sources(fixture_app):
    from types import SimpleNamespace
    client, _ = fixture_app
    outline_reply = '[{"page":1,"title":"Proposal","type":"cover"}]'
    content_reply = '{"title":"Proposal","bullets":["Ten-day sample delivery"],"speaker_notes":"Check terms"}'
    results = [SimpleNamespace(status_code=200, output=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]))
        for text in (outline_reply, content_reply)]
    with patch.object(solution, 'QwenClient') as qwen, patch('dashscope.Generation.call', side_effect=results), patch.object(
        solution.KnowledgeRetriever, 'search_multi_kb', return_value=[
            {'doc_id': 101, 'doc_name': 'Untrusted name', 'content': 'Ten-day sample delivery', 'score': 0.86}]
    ):
        qwen.return_value.api_key = 'test-key'
        outline = client.post('/api/v1/solution/outline', json={
            'topic': 'proposal', 'target_audience': 'Buyer', 'style': 'Formal', 'kb_ids': [11]}).json()
        page = client.post('/api/v1/solution/page/content', json={
            'topic': 'proposal', 'page_title': 'Proposal', 'target_audience': 'Buyer',
            'style': 'Formal', 'kb_ids': [11]}).json()
    assert outline['generation_mode'] == page['generation_mode'] == 'llm'
    assert outline['knowledge_used'] is page['knowledge_used'] is True
    assert outline['sources'][0]['doc_name'] == page['sources'][0]['doc_name'] == 'Own source'
    assert page['bullets'] == ['Ten-day sample delivery']


def test_generated_citations_are_validated_against_organization(fixture_app):
    client, _ = fixture_app
    page = {'title': 'intro', 'type': 'content', 'bullets': ['Checked fact'],
            'sources': [{'doc_id': 101, 'doc_name': 'Own source', 'content': 'safe', 'score': 0.8}]}
    forbidden = {**page, 'sources': [{**page['sources'][0], 'doc_id': 999}]}
    assert client.post('/api/v1/solution/generate', json={'topic': 'sample', 'pages': [forbidden]}).status_code == 403
    assert client.post('/api/v1/solution/generate', json={'topic': 'sample', 'pages': [page], 'template_id': '../escape.pptx'}).status_code == 400
    assert client.post('/api/v1/solution/generate', json={'topic': 'sample', 'pages': [page], 'template_id': 'unknown.pptx'}).status_code == 400
    response = client.post('/api/v1/solution/generate', json={'topic': 'sample', 'pages': [page]})
    assert response.status_code == 200
    assert response.content[:2] == b'PK'
    presentation = Presentation(io.BytesIO(response.content))
    assert len(presentation.slides) >= 1


def test_ppt_requires_org_and_pages(fixture_app):
    client, identity = fixture_app
    identity['id'] = 3
    assert client.post('/api/v1/solution/generate', json={'topic': 'test', 'pages': [{'title': 'x'}]}).status_code == 403
    identity['id'] = 1
    assert client.post('/api/v1/solution/generate', json={'topic': 'test', 'pages': []}).status_code == 422
