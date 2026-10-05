"""Real text-only acceptance against the isolated application's configured model."""
import json
from time import monotonic


def verify_marketing_text(client, checked, args):
    from routers import marketing_router
    actual_query = marketing_router.query_default_llm
    error_types = []

    def observed_query(*query_args, **query_kwargs):
        try:
            return actual_query(*query_args, **query_kwargs)
        except Exception as error:
            # Diagnostic types only: vendor messages may contain credentials.
            while error is not None and len(error_types) < 8:
                error_types.append(type(error).__name__)
                error = error.__cause__ or error.__context__
            raise

    marketing_router.query_default_llm = observed_query
    try:
        _verify(client, checked, args, error_types)
    finally:
        marketing_router.query_default_llm = actual_query


def _verify(client, checked, args, error_types):
    receipts = []
    for kind in args.marketing_kind or ['outreach_email', 'linkedin_post', 'product_article', 'seo_blog']:
        error_types.clear()
        started = monotonic()
        response = client.post('/api/v1/marketing/text/generate', json={
            'content_type': kind, 'product_name': 'Acceptance_widget',
            'selling_points': 'Fictional product MOQ 73 units, lead time 19 days. No other specifications or certifications are provided. Do not invent them.',
        })
        receipt = {'kind': kind, 'status': 'failed', 'http_status': response.status_code,
                   'seconds': round(monotonic() - started, 1)}
        if response.status_code != 200:
            receipt['error_types'] = list(error_types)
            detail = response.json().get('detail', '')
            # Only classify known application messages, never echo vendor errors.
            receipt['reason'] = ('model_call_failed' if detail == '文字模型调用失败，请检查模型配置后重试'
                                 else 'output_below_minimum' if detail == '模型没有返回符合所选类型长度要求的内容，请重试；本次未保存'
                                 else 'unexpected_response')
            assert not checked(client.get('/api/v1/marketing/text', params={'content_type': kind}))['items']
        else:
            generated = checked(response)
            assert generated['mock'] is False and '73' in generated['body'] and '19' in generated['body']
            route = f"/api/v1/marketing/text/{generated['id']}"
            restored = checked(client.get(route))
            assert restored['body'] == generated['body']
            title = 'Saved acceptance ' + kind
            body = generated['body'] + '\nInternal acceptance note: MOQ 73; lead time 19 days.'
            checked(client.patch(route, json={'title': title, 'body': body}))
            reloaded = checked(client.get(route))
            assert reloaded['title'] == title and reloaded['body'] == body
            history = checked(client.get('/api/v1/marketing/text', params={'content_type': kind}))['items']
            assert any(item['id'] == generated['id'] and item['body'] == body for item in history)
            receipt.update(status='passed', word_count=generated['word_count'], facts_preserved=True,
                           edited_body_restored=True, history_restored=True, mock=False)
        receipts.append(receipt)
        print(json.dumps(receipt), flush=True)
        if args.evidence_dir:
            args.evidence_dir.mkdir(parents=True, exist_ok=True)
            (args.evidence_dir / 'marketing-text-receipt.json').write_text(json.dumps(receipts, indent=2), encoding='utf-8')
    assert all(item['status'] == 'passed' for item in receipts), 'Some real marketing text workflows failed; see the safe receipt'
