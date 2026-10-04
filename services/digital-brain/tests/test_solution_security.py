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
from database.shared_models import SharedBase, Organization, User, KnowledgeBase, KnowledgeDoc, KnowledgeChunk, LLMModel
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
        db.add(LLMModel(name='configured-gateway', type='LLM', is_active=True, is_default=True))
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
    with patch.object(solution, 'get_default_llm_model', return_value=None), patch.object(solution.KnowledgeRetriever, 'search_multi_kb', return_value=[]):
        result = client.post('/api/v1/solution/context', json={'topic': 'sample', 'kb_ids': [11]})
        assert result.status_code == 200 and result.json()['items'] == []
        assert [log['step'] for log in result.json()['logs']] == ['Scope Validation', 'Retrieval Completed']
        outline = client.post('/api/v1/solution/outline', json={'topic': 'sample', 'kb_ids': [11]})
        page = client.post('/api/v1/solution/page/content', json={'topic': 'sample', 'kb_ids': [11], 'page_title': 'intro'})
    assert outline.status_code == page.status_code == 503
    assert 'pages' not in outline.json() and 'bullets' not in page.json()


def test_model_failures_never_claim_success(fixture_app):
    client, _ = fixture_app
    with patch.object(solution, 'query_default_llm', return_value='{"reasoning":"provider error private-key"}'), patch.object(solution.KnowledgeRetriever, 'search_multi_kb', return_value=[]):
        outline = client.post('/api/v1/solution/outline', json={'topic': 'sample'})
        page = client.post('/api/v1/solution/page/content', json={'topic': 'sample', 'page_title': 'intro'})
    assert outline.status_code == page.status_code == 502
    assert 'private-key' not in outline.text + page.text


def test_configured_model_reports_real_generation_and_only_real_sources(fixture_app):
    client, _ = fixture_app
    outline_reply = '[{"page":1,"title":"Proposal","type":"cover"}]'
    content_reply = '{"title":"Proposal","bullets":["Ten-day sample delivery"],"speaker_notes":"Check terms"}'
    with patch.object(solution, 'query_default_llm', side_effect=[outline_reply, content_reply]), patch.object(
        solution.KnowledgeRetriever, 'search_multi_kb', return_value=[
            {'doc_id': 101, 'doc_name': 'Untrusted name', 'content': 'Ten-day sample delivery', 'score': 0.86}]
    ):
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
    assert len(presentation.slides) == 1


def test_export_preserves_edited_cover_end_bullets_and_notes(fixture_app):
    client, _ = fixture_app
    pages = [
        {'title': 'Reviewed cover', 'type': 'cover', 'bullets': ['MOQ 73 units'],
         'speaker_notes': 'Reviewed remarks', 'data_source': 'Own source'},
        {'title': 'Reviewed closing', 'type': 'end', 'bullets': ['Lead time 19 days']},
    ]
    response = client.post('/api/v1/solution/generate', json={'topic': 'Original topic', 'pages': pages})
    assert response.status_code == 200
    deck = Presentation(io.BytesIO(response.content))
    assert len(deck.slides) == 2
    text = ['\n'.join(s.text for s in slide.shapes if s.has_text_frame) for slide in deck.slides]
    assert 'Reviewed cover' in text[0] and 'MOQ 73 units' in text[0]
    assert 'Reviewed closing' in text[1] and 'Lead time 19 days' in text[1]
    assert 'Reviewed remarks' in deck.slides[0].notes_slide.notes_text_frame.text
    assert 'Source: Own source' in deck.slides[0].notes_slide.notes_text_frame.text


def test_custom_template_keeps_layouts_without_example_slides(fixture_app, tmp_path, monkeypatch):
    client, _ = fixture_app
    directory = tmp_path / 'storage' / 'ppt_templates'
    directory.mkdir(parents=True)
    template = Presentation()
    example = template.slides.add_slide(template.slide_layouts[0])
    example.shapes.title.text = 'TEMPLATE EXAMPLE MUST NOT APPEAR'
    template.save(directory / 'Example.pptx')
    monkeypatch.setattr(solution, '__file__', str(tmp_path / 'routers' / 'solution_router.py'))
    response = client.post('/api/v1/solution/generate', json={
        'topic': 'Fictional terms', 'template_id': 'Example.pptx',
        'pages': [{'title': 'Reviewed terms', 'type': 'content', 'bullets': ['MOQ 73 units']}],
    })
    assert response.status_code == 200
    deck = Presentation(io.BytesIO(response.content))
    assert len(deck.slides) == 1 and len(deck.slide_layouts) == len(template.slide_layouts)
    shapes = [shape for shape in deck.slides[0].shapes if shape.has_text_frame and shape.text]
    assert 'TEMPLATE EXAMPLE' not in '\n'.join(shape.text for shape in shapes)
    assert 'MOQ 73 units' in '\n'.join(shape.text for shape in shapes)
    assert all(shape.left >= 0 and shape.left + shape.width <= deck.slide_width for shape in shapes)


def test_ppt_requires_org_and_pages(fixture_app):
    client, identity = fixture_app
    identity['id'] = 3
    assert client.post('/api/v1/solution/generate', json={'topic': 'test', 'pages': [{'title': 'x'}]}).status_code == 403
    identity['id'] = 1
    assert client.post('/api/v1/solution/generate', json={'topic': 'test', 'pages': []}).status_code == 422


def test_draft_save_edit_reload_and_scope(fixture_app):
    client, identity = fixture_app
    state = {'settings': {'topic': 'Fictional product', 'kb_ids': [11]}, 'pages': [
        {'id': '1', 'outline': {'page': 1, 'title': 'Terms', 'type': 'content'},
         'content': {'title': 'Terms', 'bullets': ['MOQ 73', 'Lead time 19 days'],
                     'sources': [{'doc_id': 101, 'doc_name': 'Own source', 'content': 'Public fixture', 'score': 1}]}}
    ]}
    response = client.post('/api/v1/solution/drafts', json=state)
    assert response.status_code == 201
    draft_id = response.json()['id']
    assert client.get('/api/v1/solution/drafts').json()['items'][0]['id'] == draft_id
    state['pages'][0]['content']['title'] = 'Reviewed terms'
    assert client.put(f'/api/v1/solution/drafts/{draft_id}', json=state).status_code == 200
    restored = client.get(f'/api/v1/solution/drafts/{draft_id}').json()['state']
    assert restored['pages'][0]['content']['title'] == 'Reviewed terms'
    assert restored['pages'][0]['content']['bullets'] == ['MOQ 73', 'Lead time 19 days']
    state['pages'][0]['content']['sources'][0]['doc_id'] = 999
    assert client.put(f'/api/v1/solution/drafts/{draft_id}', json=state).status_code == 403
    identity['id'] = 2
    assert client.get('/api/v1/solution/drafts').json()['items'] == []
    assert client.get(f'/api/v1/solution/drafts/{draft_id}').status_code == 404
    assert client.put(f'/api/v1/solution/drafts/{draft_id}', json=state).status_code == 404
