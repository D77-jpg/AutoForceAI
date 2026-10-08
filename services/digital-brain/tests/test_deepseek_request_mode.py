"""Exercise actual SDK serialization through the application's model runtime."""
import json

import httpx
import pytest
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.llm import runtime
from core.llm.providers.openai_generic import OpenAIGenericLLM
from database import models
from database.base import Base
from database.shared_models import LLMModel


@pytest.mark.parametrize('name,thinking,expected', [
    ('deepseek-flash', False, 'disabled'),
    ('deepseek-v4-pro', True, 'enabled'),
    ('deepseek-flash', None, None),
    ('custom-gateway-model', False, None),
])
def test_bounded_runtime_serializes_mode_only_for_deepseek(monkeypatch, name, thinking, expected):
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        chunks = [
            {'id': 'test-request', 'object': 'chat.completion.chunk', 'created': 0, 'model': name,
             'choices': [{'index': 0, 'delta': {'content': 'MOQ 73; lead time 19 days'}, 'finish_reason': None}]},
            {'id': 'test-request', 'object': 'chat.completion.chunk', 'created': 0, 'model': name,
             'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]},
        ]
        body = ''.join('data: ' + json.dumps(chunk) + '\n\n' for chunk in chunks) + 'data: [DONE]\n\n'
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=body)

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        llm = OpenAIGenericLLM(api_key='synthetic-test-key', base_url='https://example.invalid', model=name)
        llm.client.close()
        llm.client = OpenAI(api_key='synthetic-test-key', base_url='https://example.invalid', http_client=transport)
        monkeypatch.setattr(runtime.ModelFactory, 'get_provider', lambda *args, **kwargs: llm)
        monkeypatch.setattr(runtime.CostMonitor, 'log_request', lambda **kwargs: None)
        with sessionmaker(bind=engine)() as db:
            db.add(LLMModel(name=name, display_name=name, type='LLM', is_active=True, is_default=True))
            db.commit()
            result = runtime.query_default_llm(db, 'Fictional terms', stream=True, max_tokens=3500, thinking=thinking)
        assert result == 'MOQ 73; lead time 19 days'
        assert len(requests) == 1 and requests[0]['max_tokens'] == 3500
        if expected is None:
            assert 'thinking' not in requests[0]
        else:
            assert requests[0]['thinking'] == {'type': expected}
    engine.dispose()
