"""Exercise real local workflows in a fresh database, using the configured LLM.

Run with services/digital-brain/venv/Scripts/python.exe. --serve retains this
isolated instance on loopback for browser checks; no CRM/publishing worker starts.
Only the selected model configuration is read from the source DB. No live business
records are copied or changed. The temporary model credentials are removed on exit.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import secrets
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / 'services' / 'digital-brain'


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-source', type=Path, default=SERVICE / 'geo_mind_v2.db')
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--real-llm', action='store_true', help='Explicitly enable the configured model call with synthetic data only')
    parser.add_argument('--external-services', action='store_true', help='Test Beijing embedding and Wanx plus Serper using public facts only')
    parser.add_argument('--allowed-model-origin', help='Approved model origin, required with --real-llm; rejects a different configured destination')
    parser.add_argument('--port', type=int, default=8011)
    args = parser.parse_args()
    # Read-only connection; do not import the live application's configured engine.
    model = None
    provider = None
    if args.real_llm:
        with sqlite3.connect(args.model_source.resolve().as_uri() + '?mode=ro', uri=True) as source:
          source.row_factory = sqlite3.Row
          row = source.execute("SELECT id, provider_id, name, display_name, type, api_key, base_url, context_window, is_active, is_default, is_kb_search_default, supports_chat, supports_geo FROM llm_models WHERE is_active=1 AND type='LLM' ORDER BY is_default DESC, id LIMIT 1").fetchone()
          if row is None:
              raise RuntimeError('No configured LLM; acceptance cannot use a mock')
          model = dict(row)
          provider = source.execute('SELECT id, name, api_key, base_url, is_active FROM llm_providers WHERE id=?', (model['provider_id'],)).fetchone() if model['provider_id'] else None
          provider = dict(provider) if provider else None
          if provider and not provider['is_active']:
              raise RuntimeError('Configured model provider is disabled')
    from dotenv import load_dotenv
    load_dotenv(SERVICE / '.env')
    dashscope_key = os.getenv('DASHSCOPE_API_KEY') if args.external_services else None
    if args.external_services and not (dashscope_key and os.getenv('SERPER_API_KEY')):
        raise RuntimeError('External acceptance requires Beijing DashScope and Serper configuration')
    if model:
        name = model['name'].lower()
        key_name = 'DASHSCOPE_API_KEY' if 'qwen' in name else 'ZHIPUAI_API_KEY' if 'glm' in name or 'zhipu' in name else 'DEEPSEEK_API_KEY' if 'deepseek' in name else 'OPENAI_API_KEY'
        model['api_key'] = model['api_key'] or (provider['api_key'] if provider else None) or os.getenv(key_name)
        model['base_url'] = model['base_url'] or (provider['base_url'] if provider else None) or os.getenv('OPENAI_BASE_URL')
        approved = urlsplit(args.allowed_model_origin or '')
        destination = urlsplit(model['base_url'] or '')
        def origin(url):
            return (url.scheme, url.hostname, url.port or (443 if url.scheme == 'https' else 80))
        if (approved.scheme not in ('http', 'https') or not approved.hostname
                or approved.username or approved.password or destination.username or destination.password
                or origin(destination) != origin(approved)):
            raise RuntimeError('Model destination must match the explicitly approved origin')
    # Embedding fallback must not silently send even synthetic data to a second
    # provider. This run verifies lexical retrieval; semantic retrieval is separate.
    for key in ('OPENAI_API_KEY', 'DASHSCOPE_API_KEY', 'ZHIPUAI_API_KEY', 'DEEPSEEK_API_KEY'):
        os.environ[key] = ''
    if args.external_services:
        os.environ['DASHSCOPE_API_KEY'] = dashscope_key
    os.chdir(SERVICE)
    sys.path.insert(0, str(SERVICE))
    upload_paths = []
    external_failures = []
    with tempfile.TemporaryDirectory(prefix='autoforce-local-acceptance-') as temporary:
        # Cleanup may only target the exact directory created for this run.
        assert Path(temporary).resolve().parent == Path(tempfile.gettempdir()).resolve()
        os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(temporary) / 'acceptance.db').replace('\\', '/')
        os.environ['APP_ENV'] = 'development'
        os.environ['JWT_SECRET'] = secrets.token_urlsafe(48)
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from core.db_manager import SHARED_ENGINE, SharedSessionLocal
        from database.base import Base
        from database.shared_models import LLMModel, LLMProvider, KnowledgeDoc, KnowledgeChunk
        from routers import auth_router, agent_router, kb_router, brain_router, platform_router, marketing_router
        # All uploaded/generated files also stay inside the temporary run directory.
        kb_router.UPLOAD_ROOT = str(Path(temporary) / 'documents')
        import core.marketing_images as images
        images.IMAGE_ROOT = Path(temporary) / 'images'
        marketing_router.IMAGE_ROOT = images.IMAGE_ROOT
        Base.metadata.create_all(SHARED_ENGINE)
        with SharedSessionLocal() as db:
            if provider:
                db.add(LLMProvider(**provider))
                db.flush()
            if model:
                db.add(LLMModel(**model))
            db.commit()
        app = FastAPI()
        for module in (auth_router, agent_router, kb_router, brain_router, platform_router, marketing_router):
            app.include_router(module.router)
        def checked(response, code=200):
            if response.status_code != code:
                raise RuntimeError(f'HTTP workflow failed: {response.status_code}')
            return response.json()
        try:
            with TestClient(app) as client:
                account = checked(client.post('/auth/register', json={'email': 'acceptance@example.invalid', 'password': 'Local-Acceptance-only!2026'}), 201)
                client.headers['Authorization'] = 'Bearer ' + account['access_token']
                membership = checked(client.post('/auth/organization/create', json={'name': 'Isolated local acceptance'}))
                client.headers['Authorization'] = 'Bearer ' + membership['access_token']
                checked(client.post('/auth/login', json={'email': 'acceptance@example.invalid', 'password': 'Local-Acceptance-only!2026'}))
                project = checked(client.post('/agents/projects', json={'name': 'Acceptance project'}), 201)
                employee = checked(client.post(f"/agents/{project['id']}/employees/from-template", json={'template_key': 'lead_researcher', 'name': 'Acceptance researcher'}))
                checked(client.patch(f"/agents/{project['id']}/employees/{employee['id']}", json={'name': 'Saved researcher'}))
                assert checked(client.get(f"/agents/{project['id']}/employees"))[0]['name'] == 'Saved researcher'
                library = checked(client.post('/api/v1/kb/bases', json={'name': 'Acceptance public facts' if args.external_services else 'Acceptance product specs', 'is_public': True}))
                facts = b'Paris is the capital of France. Tokyo is the capital of Japan.' if args.external_services else b'Acceptance_widget MOQ is 73 units. Acceptance_widget lead time is 19 days.'
                upload = checked(client.post(f"/api/v1/kb/bases/{library['id']}/docs", files={'file': ('acceptance.txt', facts, 'text/plain')}))
                with SharedSessionLocal() as db:
                    doc = db.query(KnowledgeDoc).one()
                    upload_paths.append(Path(doc.file_path).resolve())
                    assert doc.status in ('indexed', 'embedded') and doc.chunk_count > 0
                    if args.external_services:
                        if doc.status != 'embedded':
                            external_failures.append('embedding')
                            print(json.dumps({'embedding': 'failed', 'lexical_fallback_not_counted': True}), flush=True)
                        else:
                            vector = db.query(KnowledgeChunk).one().embedding
                            assert vector is not None and len(vector) == 1024
                            from core.rag.retriever import KnowledgeRetriever
                            retriever = KnowledgeRetriever(db)
                            assert retriever._lexical_search([library['id']], '法国的首都是哪座城市？', 5) == []
                            hits = retriever._vector_search([library['id']], '法国的首都是哪座城市？', 5)
                            assert hits and 'Paris' in hits[0]['content']
                            print(json.dumps({'embedding': 'passed', 'dimensions': 1024, 'semantic_only_hits': len(hits)}), flush=True)
                question = 'According to the uploaded document, what is the capital of France? Cite the source.' if args.external_services else 'What are the MOQ and lead time for Acceptance_widget? Cite the uploaded document.'
                response = client.post('/api/v1/brain/chat', json={'query': question, 'kb_ids': [library['id']]})
                events = [json.loads(line) for line in response.text.splitlines()]
                print(json.dumps({'chat_events': {kind: sum(event['t'] == kind for event in events) for kind in {event['t'] for event in events}}, 'retrieved_sources': sum(len(event.get('sources', [])) for event in events if event['t'] == 'meta')}, ensure_ascii=False), flush=True)
                session_id = events[0]['session_id']
                history = checked(client.get(f'/api/v1/brain/sessions/{session_id}/messages'))
                if args.real_llm:
                    assert events[-1]['t'] == 'done', 'Real model call did not complete; no fallback is accepted'
                    answer = ''.join(event.get('chunk', '') for event in events if event['t'] == 'token')
                    print(json.dumps({'synthetic_answer': answer}, ensure_ascii=False), flush=True)
                    if args.external_services:
                        assert 'Paris' in answer, 'Answer did not use the public uploaded facts'
                    else:
                        assert '73' in answer, 'Answer did not use the uploaded facts'
                        assert '19' in answer, 'Answer did not use the uploaded lead time'
                    assert '[1]' in answer, 'Answer did not cite the document inline'
                    assert any(event.get('sources') for event in events if event['t'] == 'meta'), 'Missing document citations'
                    assert history[-1]['content'] == answer and history[-1]['citations']
                else:
                    assert events[-1]['t'] == 'error' and all(e['t'] != 'done' for e in events)
                    assert not any(m['role'] == 'assistant' for m in history)
                assert checked(client.get('/api/v1/brain/sessions'))[0]['id'] == session_id
                if args.external_services:
                    from core.tools.web_search import WebSearchTool
                    search = json.loads(WebSearchTool().run({'query': 'Alibaba Cloud Model Studio official documentation', 'num': 3}))
                    assert not search.get('error') and search.get('results') and search['provider'] == 'serper'
                    print(json.dumps({'web_search': 'passed', 'real_results': len(search['results'])}), flush=True)
                    # One public, generic image. No existing business assets are sent.
                    image_response = client.post('/api/v1/marketing/images/generate', json={'prompt': 'A simple blue geometric cube on a white background, no text', 'product_name': 'Public geometric cube'})
                    if image_response.status_code != 200:
                        external_failures.append('image_generation')
                        print(json.dumps({'image_generation': 'failed', 'http_status': image_response.status_code, 'reason': image_response.json().get('detail')}), flush=True)
                    else:
                        generated = checked(image_response)
                        assert generated['mock'] is False and generated['url'].startswith('/api/v1/marketing/images/')
                        saved_image = client.get(generated['url'])
                        assert saved_image.status_code == 200 and len(saved_image.content) > 1024
                        from io import BytesIO
                        from PIL import Image
                        with Image.open(BytesIO(saved_image.content)) as decoded:
                            decoded.verify()
                        restored = checked(client.get('/api/v1/marketing/images'))['items'][0]
                        assert restored['image_url'] == generated['url']
                        assert client.get(restored['image_url']).content == saved_image.content
                        print(json.dumps({'image_generation': 'passed', 'saved_bytes': len(saved_image.content), 'history_restored': True, 'decoded_image': True}), flush=True)
                    if args.real_llm:
                        text = checked(client.post('/api/v1/marketing/text/generate', json={'content_type': 'outreach_email', 'product_name': 'Acceptance_widget', 'selling_points': 'Fictional product MOQ 73 units, lead time 19 days. No other specifications or certifications are provided.'}))
                        assert text['mock'] is False and '73' in text['body'] and '19' in text['body']
                        restored_text = checked(client.get(f"/api/v1/marketing/text/{text['id']}"))
                        assert restored_text['body'] == text['body']
                        edited = checked(client.patch(f"/api/v1/marketing/text/{text['id']}", json={'title': 'Saved acceptance outreach', 'body': text['body']}))
                        reloaded = checked(client.get(f"/api/v1/marketing/text/{text['id']}"))
                        assert reloaded['title'] == edited['title'] == 'Saved acceptance outreach'
                        assert reloaded['body'] == text['body'] and reloaded['word_count'] == text['word_count']
                        print(json.dumps({'marketing_text': 'passed', 'word_count': text['word_count'], 'history_restored': True}), flush=True)
                    checked(client.patch(f"/api/v1/kb/bases/{library['id']}", json={'name': 'Saved public acceptance facts', 'is_public': True}))
                    checked(client.put('/api/v1/kb/config', json={'top_k': 3, 'score_threshold': 0.25, 'chunk_size': 800, 'chunk_overlap': 100}))
                    assert checked(client.get('/api/v1/kb/config'))['top_k'] == 3
                overview = checked(client.get('/api/v1/platform/overview'))
                assert overview['total_models'] == (1 if args.real_llm else 0)
                scope = ['email login', 'organization JWT', 'project create', 'employee create/edit/reload', 'knowledge upload/index', 'saved history reload', 'platform overview']
                scope += ['real model answer', 'citations'] if args.real_llm else ['unconfigured model fails without fake success']
                print(json.dumps({'status': 'partial' if external_failures else 'passed', 'external_failures': external_failures, 'scope': scope, 'retrieval': doc.status, 'real_model_verified': args.real_llm, 'mock_used': False}, ensure_ascii=False), flush=True)
                if args.real_llm:
                    print(json.dumps({'answer': answer, 'citations_saved': len(history[-1]['citations']), 'history_restored': True}, ensure_ascii=False), flush=True)
            if args.serve:
                import uvicorn
                print(f'Isolated browser acceptance: http://127.0.0.1:{args.port}', flush=True)
                uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning')
        finally:
            with SharedSessionLocal() as db:
                upload_paths.extend(Path(d.file_path).resolve() for d in db.query(KnowledgeDoc).all() if d.file_path)
            upload_root = (SERVICE / kb_router.UPLOAD_ROOT).resolve()
            for file in set(upload_paths):
                if file.is_relative_to(upload_root):
                    file.unlink(missing_ok=True)
            SHARED_ENGINE.dispose()
    if external_failures:
        raise RuntimeError('Some external workflows failed; no full acceptance claimed')


if __name__ == '__main__':
    try:
        run()
    except Exception as error:
        # Vendor/driver errors can contain endpoint credentials. Keep output safe.
        print(f'Local functional acceptance failed ({type(error).__name__}). No mock or fallback counted as success.', file=sys.stderr)
        if isinstance(error, AssertionError):
            print(str(error), file=sys.stderr)
        sys.exit(1)
