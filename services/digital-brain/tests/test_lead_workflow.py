"""Tenant isolation, durable edits and safe export of actual lead records."""
import csv
import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.db_manager import get_shared_db
from core.dependencies import get_current_user
from database.base import Base
from database.shared_models import Organization, User, Lead, CrmIntegrationConfig, CrmSyncJob
from routers import lead_router, quotation_router


@pytest.fixture
def env():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add_all([Organization(id=1, name='A'), Organization(id=2, name='B')])
        db.flush()
        db.add_all([User(id=1, username='a', organization_id=1), User(id=2, username='b', organization_id=2), User(id=3, username='no-org')])
        db.add(CrmIntegrationConfig(organization_id=1, project_id='project-a', enabled=True))
        db.commit()
    identity = {'id': 1}
    app = FastAPI()
    app.include_router(lead_router.router)
    app.include_router(quotation_router.router)
    def database():
        with factory() as db:
            yield db
    app.dependency_overrides[get_shared_db] = database
    app.dependency_overrides[get_current_user] = lambda: identity
    with TestClient(app) as client:
        yield client, factory, identity
    engine.dispose()


def test_create_dedup_edit_and_outbox_same_transaction(env):
    client, factory, _ = env
    first = client.post('/api/v1/leads', json={'email': ' TEST@example.invalid ', 'company': 'Synthetic', 'products': 'Product MOQ 73'})
    assert first.status_code == 200
    lead_id = first.json()['id']
    assert first.json()['email'] == 'test@example.invalid'
    second = client.post('/api/v1/leads', json={'email': 'TEST@example.invalid', 'name': 'Buyer'})
    assert second.json()['id'] == lead_id
    edited = client.patch(f'/api/v1/leads/{lead_id}', json={'company': 'Reviewed', 'products': '19 days', 'status': 'contacted'})
    assert edited.status_code == 200
    restored = client.get('/api/v1/leads').json()['items'][0]
    assert restored['company'] == 'Reviewed' and restored['status'] == 'contacted'
    assert client.get('/api/v1/leads/summary').json()['by_status']['contacted'] == 1
    with factory() as db:
        assert db.query(Lead).count() == 1
        assert db.query(CrmSyncJob).filter(CrmSyncJob.lead_id == lead_id).count() == 3
    assert client.patch(f'/api/v1/leads/{lead_id}', json={'status': None}).status_code == 400
    assert client.patch(f'/api/v1/leads/{lead_id}', json={'organization_id': 2}).status_code == 422


def test_all_routes_reject_unbound_users_and_other_tenants(env):
    client, factory, identity = env
    lead_id = client.post('/api/v1/leads', json={'email': 'same@example.invalid', 'session_uuid': 'shared-session'}).json()['id']
    identity['id'] = 2
    assert client.get('/api/v1/leads').json()['items'] == []
    other = client.post('/api/v1/leads', json={'email': 'same@example.invalid', 'session_uuid': 'shared-session'})
    assert other.json()['id'] != lead_id
    assert client.patch(f'/api/v1/leads/{lead_id}', json={'status': 'converted'}).status_code == 404
    assert client.get('/api/v1/leads/summary').json()['total'] == 1
    with factory() as db:
        legacy = lead_router.upsert_lead(db, None, {'email': 'same@example.invalid', 'session_uuid': 'shared-session'})
        assert legacy.id not in (lead_id, other.json()['id'])
    identity['id'] = 3
    for method, path, body in [('GET', '', None), ('GET', '/summary', None), ('GET', '/export.csv', None), ('POST', '', {'name': 'X'}), ('PATCH', f'/{lead_id}', {'status': 'converted'})]:
        assert client.request(method, '/api/v1/leads' + path, json=body).status_code == 403


def test_edit_duplicate_email_rejected_and_csv_formulas_escaped(env):
    client, _, _ = env
    first = client.post('/api/v1/leads', json={'email': 'one@example.invalid', 'company': '=1+1'}).json()
    second = client.post('/api/v1/leads', json={'email': 'two@example.invalid'}).json()
    assert client.patch(f"/api/v1/leads/{second['id']}", json={'email': 'ONE@example.invalid'}).status_code == 409
    rows = list(csv.DictReader(io.StringIO(client.get('/api/v1/leads/export.csv').text)))
    assert next(row for row in rows if row['id'] == str(first['id']))['company'] == "'=1+1"
    assert client.post('/api/v1/leads', json={}).status_code == 422
    assert client.post('/api/v1/leads', json={'email': 'not-an-email'}).status_code == 422


def test_quote_detail_pdf_and_history_require_active_organization_mapping(env, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from database.shared_models import CrmEntityLink
    from core.crm.client import QuotationPdfDownload
    client, factory, identity = env
    lead_id = client.post('/api/v1/leads', json={'email': 'mapped@example.invalid'}).json()['id']
    with factory() as db:
        db.query(CrmIntegrationConfig).one().service_token = 'only-unit-test'
        db.add(CrmEntityLink(organization_id=1, lead_id=lead_id, provider='genesis_crm', project_id='project-a', remote_customer_id='owned'))
        db.commit()
    crm = MagicMock()
    crm.get_quotation.return_value = SimpleNamespace(customerId='other-customer', quotationId='q1')
    monkeypatch.setattr(quotation_router, 'client_from_config', lambda *a, **k: crm)
    assert client.get('/api/v1/crm/quotations/q1').status_code == 404
    assert client.get('/api/v1/crm/quotations/q1/pdf').status_code == 404
    crm.download_quotation_pdf.assert_not_called()
    crm.get_quotation.return_value = SimpleNamespace(customerId='owned', quotationId='q1')
    crm.download_quotation_pdf.return_value = QuotationPdfDownload(b'%PDF-1.3', 'etag', '1', None)
    crm.get_customer_quotations.return_value = {'items': [{'quotationId': 'q1'}]}
    assert client.get('/api/v1/crm/quotations/q1').json()['quotation']['customerId'] == 'owned'
    assert client.get('/api/v1/crm/quotations/q1/pdf').content == b'%PDF-1.3'
    assert client.get(f'/api/v1/crm/quotations/leads/{lead_id}').json()['items'][0]['quotationId'] == 'q1'
    crm.get_customer_quotations.assert_called_once_with(f'lead:{lead_id}')
    identity['id'] = 2
    assert client.get(f'/api/v1/crm/quotations/leads/{lead_id}').status_code == 409
    assert client.get('/api/v1/crm/quotations/q1/pdf').status_code == 409
