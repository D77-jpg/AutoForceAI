"""Image persistence rejects invalid files and unsafe result destinations."""
import pytest
from fastapi import HTTPException
from core import marketing_images
from core.rag.embedder import EmbeddingClient, EmbeddingUnavailable


@pytest.mark.parametrize('url', [
    'http://example.aliyuncs.com/image.png',
    'https://localhost/image.png',
    'https://example.aliyuncs.com.evil.invalid/image.png',
    'https://key@example.aliyuncs.com/image.png',
])
def test_result_destination_is_checked_before_download(url, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail('unsafe destination must never be contacted')
    monkeypatch.setattr(marketing_images.requests, 'get', unexpected)
    with pytest.raises(HTTPException) as error:
        marketing_images.store_image(url)
    assert error.value.status_code == 502


@pytest.mark.parametrize('body', [b'<html>error</html>', b'', b'x' * 25])
def test_invalid_or_oversized_file_does_not_create_success_file(monkeypatch, tmp_path, body):
    class Response:
        status_code = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, *args): yield body
    monkeypatch.setattr(marketing_images.requests, 'get', lambda *args, **kwargs: Response())
    monkeypatch.setattr(marketing_images, 'IMAGE_ROOT', tmp_path)
    monkeypatch.setattr(marketing_images, 'MAX_IMAGE_BYTES', 20)
    with pytest.raises(HTTPException):
        marketing_images.store_image('https://fixture.aliyuncs.com/image.png')
    assert list(tmp_path.iterdir()) == []


def test_exhausted_free_embedding_quota_does_not_retry_or_leak_response(monkeypatch):
    client = EmbeddingClient()
    client.model_name, client.base_url, client.api_key = 'text-embedding-v3', 'https://fixture.invalid', 'private-key'
    calls = []
    class Response:
        status_code = 400
        text = 'Free quota exhausted private-key'
        def json(self): return {'error': {'code': 'AllocationQuota.FreeTierOnly', 'message': self.text}}
    monkeypatch.setattr('core.rag.embedder.requests.post', lambda *args, **kwargs: calls.append(args) or Response())
    with pytest.raises(EmbeddingUnavailable) as error:
        client.embed_query('Public fact')
    assert len(calls) == 1
    assert 'private-key' not in str(error.value)
    assert '免费额度' in str(error.value)
