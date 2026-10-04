"""Real HTTP integration receipts against the isolated Genesis application."""
import csv
import io
import json
import os
import socket

import httpx


def verify_crm(client, checked, factory, args, kb_id):
    from core.crm.dispatcher import dispatch_once
    from core.crm.outcome_poller import poll_all_outcomes
    from database.shared_models import CrmIntegrationConfig, CrmSyncJob, CrmOutcomeEvent

    base = os.environ['ACCEPTANCE_CRM_URL']
    assert base == 'http://127.0.0.1:5012/api', 'Only the isolated loopback Genesis fixture is permitted'
    config = {'base_url': base, 'project_id': os.environ['ACCEPTANCE_CRM_PROJECT'], 'service_token': os.environ['ACCEPTANCE_CRM_TOKEN']}
    if os.getenv('ACCEPTANCE_CRM_WEB_URL'):
        config['web_base_url'] = os.environ['ACCEPTANCE_CRM_WEB_URL']
    saved = checked(client.put('/api/v1/crm/integration/config', json=config))
    assert 'service_token' not in saved['config'] and not saved['config']['enabled']
    assert checked(client.post('/api/v1/crm/integration/test'))['ok']
    checked(client.post('/api/v1/crm/integration/enable'))
    lead = checked(client.post('/api/v1/leads', json={
        'email': 'buyer@example.invalid', 'company': 'Fictional acceptance buyer',
        'name': 'Test buyer', 'products': 'Acceptance_widget',
        'conversation': 'Fictional Acceptance_widget MOQ 73 units, lead time 19 days.',
    }))
    duplicate = checked(client.post('/api/v1/leads', json={'email': 'BUYER@example.invalid', 'company': 'Reviewed fictional buyer'}))
    assert duplicate['id'] == lead['id']
    checked(client.patch(f"/api/v1/leads/{lead['id']}", json={'status': 'contacted'}))
    with factory() as db:
        assert dispatch_once(db, 'acceptance') >= 1
    row = checked(client.get('/api/v1/leads'))['items'][0]
    assert row['crm']['synced'] and row['crm']['job_status'] == 'succeeded'
    customer_id = row['crm']['remote_customer_id']
    crm_headers = {'Authorization': 'Bearer ' + config['service_token'], 'X-Project-Id': config['project_id']}
    remote = httpx.get(base + f"/integrations/v1/customers/lead:{lead['id']}", headers=crm_headers, timeout=15)
    assert remote.status_code == 200 and remote.json()['data']['customerId'] == customer_id

    # Real connection refusal, not a mocked client/response. Confined to this DB.
    with socket.socket() as unused:
        unused.bind(('127.0.0.1', 0))
        closed_port = unused.getsockname()[1]
    failure_lead = checked(client.post('/api/v1/leads', json={'email': 'retry@example.invalid', 'company': 'Retry fictional buyer'}))
    with factory() as db:
        cfg = db.query(CrmIntegrationConfig).one()
        cfg.base_url = f'http://127.0.0.1:{closed_port}/api'
        db.commit()
        dispatch_once(db, 'acceptance-fault')
        failed = db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == failure_lead['id']).one()
        assert failed.status == 'retrying' and failed.attempt_count == 1
        job_id = failed.id
        cfg.base_url = base
        db.commit()
    checked(client.post(f'/api/v1/crm/integration/jobs/{job_id}/retry'))
    with factory() as db:
        dispatch_once(db, 'acceptance-recovery')
        assert db.get(CrmSyncJob, job_id).status == 'succeeded'

    proposal_response = client.post('/api/v1/crm/quotations/proposals', json={'leadId': lead['id'], 'currency': 'USD', 'knowledgeBaseIds': [kb_id]})
    if args.real_llm:
        proposal = checked(proposal_response)
        assert proposal['model'] != 'rules-fallback' and any(s['kind'] == 'knowledge' for s in proposal['sources'])
        assert proposal['items'] and proposal['items'][0]['unitPrice'] is None
        assert '73' in str(proposal.get('moq')) and '19' in str(proposal.get('leadTime'))
        # Quantity and unit price are explicit HUMAN test inputs, never sent to LLM.
        proposal_id, sources, model = proposal['proposalId'], proposal['sources'], proposal['model']
    else:
        assert proposal_response.status_code == 503, 'Missing LLM must fail, not return a template success'
        proposal_id, sources, model = 'quote-proposal:manual-acceptance', [{'kind': 'lead', 'referenceId': f"lead:{lead['id']}"}], None
    confirm = {'leadId': lead['id'], 'proposalId': proposal_id, 'sources': sources, 'model': model, 'confirmed': True, 'quotation': {
        'title': 'Reviewed fictional acceptance quote', 'currency': 'USD',
        'items': [{'productName': 'Acceptance_widget', 'quantity': 73, 'unitPrice': 2.5}],
        'moq': '73 units', 'leadTime': '19 days',
    }}
    result = checked(client.post('/api/v1/crm/quotations/confirm', json=confirm))
    replay = checked(client.post('/api/v1/crm/quotations/confirm', json=confirm))
    quote = result['quotation']
    assert quote['quotationId'] == replay['quotation']['quotationId'] and quote['totalAmount'] == 182.5
    assert quote['status'] == 'draft'
    history = checked(client.get(f"/api/v1/crm/quotations/leads/{lead['id']}"))
    assert len(history['items']) == 1 and history['items'][0]['quotationId'] == quote['quotationId']
    detail = checked(client.get(f"/api/v1/crm/quotations/{quote['quotationId']}"))
    assert detail['quotation'] == quote
    pdf = client.get(result['pdfUrl'])
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF-') and len(pdf.content) > 1000
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf.content))
    extracted = '\n'.join(page.extract_text() for page in reader.pages)
    assert '182.50' in extracted and '19 days' in extracted and '73' in extracted
    etag = pdf.headers['etag']
    assert client.get(result['pdfUrl'], headers={'If-None-Match': etag}).status_code == 304

    # Sales uses the actual Genesis authenticated business API to mark won.
    login = httpx.post(base + '/auth/login', json={'username': 'acceptance', 'password': os.environ['ACCEPTANCE_CRM_PASSWORD']}, timeout=15)
    assert login.status_code == 200
    sales_headers = {'Authorization': 'Bearer ' + login.json()['data']['token'], 'X-Project-Id': config['project_id']}
    change = httpx.put(base + f'/customers/{customer_id}', headers=sales_headers, json={'status': 'won'}, timeout=15)
    assert change.status_code == 200
    with factory() as db:
        assert poll_all_outcomes(db, 'acceptance-outcome') == 1
        assert poll_all_outcomes(db, 'acceptance-outcome') == 0
        assert db.query(CrmOutcomeEvent).count() == 1
    won = next(item for item in checked(client.get('/api/v1/leads'))['items'] if item['id'] == lead['id'])
    assert won['status'] == 'converted' and won['crm']['remote_status'] == 'won'
    summary = checked(client.get('/api/v1/leads/summary'))
    assert summary['total'] == 2 and summary['by_status']['converted'] == 1
    csv_rows = list(csv.DictReader(io.StringIO(client.get('/api/v1/leads/export.csv').text)))
    assert len(csv_rows) == 2
    factory.kw['bind'].dispose()
    assert checked(client.get(f"/api/v1/crm/quotations/{quote['quotationId']}"))['quotation']['totalAmount'] == 182.5
    project_branding_verified = 'Fictional test supplier' in extracted
    receipt = {'crm': 'passed', 'real_genesis_http': True, 'real_mongodb': True, 'mock_used': False, 'lead_dedup': True,
               'delivery_failure_retry_recovery': True, 'outcome_won_replayed_once': True, 'quotation_idempotent': True,
               'quotation_restored': True, 'quotation_total': 182.5, 'pdf_bytes': len(pdf.content), 'pdf_pages': len(reader.pages),
               'pdf_etag_304': True, 'ai_proposal_verified': args.real_llm, 'external_publish_or_mail_sent': False,
               'pdf_project_branding_verified': project_branding_verified,
               'pending': [] if project_branding_verified else ['quotation_project_branding']}
    if args.evidence_dir:
        args.evidence_dir.mkdir(parents=True, exist_ok=True)
        (args.evidence_dir / 'crm-quotation.pdf').write_bytes(pdf.content)
        (args.evidence_dir / 'crm-api-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt), flush=True)
    return receipt
