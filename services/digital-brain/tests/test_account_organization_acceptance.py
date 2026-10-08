"""Real JWT/HTTP membership and account lifecycle in an isolated database."""
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core import dependencies
from core.auth import create_access_token, decode_token
from core.db_manager import get_shared_db
from database.base import Base
from database import models  # Register all ORM relationships.
from database.shared_models import User
from routers import admin_router, auth_router

PASSWORD = 'Local-Account-Acceptance!2026'


@pytest.fixture
def accounts(monkeypatch):
    monkeypatch.setenv('JWT_SECRET', 'isolated-account-acceptance-key-with-adequate-length')
    monkeypatch.setattr(auth_router, 'ALLOW_EMAIL_REGISTER', True)
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(dependencies, 'SharedSessionLocal', factory)
    # Rate limiting has its own suite; keep these independent of shared counters.
    monkeypatch.setattr(dependencies, 'enforce_user_rate_limit', lambda request: None)
    app = FastAPI()
    app.include_router(auth_router.router)
    app.include_router(admin_router.router)

    def database():
        with factory() as db:
            yield db
    app.dependency_overrides[get_shared_db] = database
    with TestClient(app) as client:
        def register(name):
            response = client.post('/auth/register', json={'email': f'{name}@example.invalid', 'password': PASSWORD})
            assert response.status_code == 201
            return response.json()
        root, owner, member = [register(name) for name in ('system', 'owner', 'member')]
        response = client.post('/auth/organization/create', headers=auth(owner), json={'name': 'Acceptance Company'})
        assert response.status_code == 200
        owner = response.json()
        yield client, factory, root, owner, member, register
    engine.dispose()


def auth(account):
    return {'Authorization': 'Bearer ' + account['access_token']}


def join(client, account, owner):
    return client.post('/auth/organization/join', headers=auth(account), json={
        'name': owner['organization_name'], 'invite_code': owner['invite_code'],
    })


def test_join_returns_usable_jwt_and_refresh_remains_authenticated(accounts):
    client, _, _, owner, member, _ = accounts
    bad = client.post('/auth/organization/join', headers=auth(member), json={'name': owner['organization_name'], 'invite_code': 'invalid'})
    assert bad.status_code == 403
    response = join(client, member, owner)
    assert response.status_code == 200
    joined = response.json()
    claims = decode_token(joined['access_token'])
    assert claims and claims['org_id'] == owner['organization_id'] and claims['role'] == 'user'
    me = client.get('/auth/me', headers=auth(joined))
    assert me.status_code == 200 and me.json()['organization_id'] == owner['organization_id']
    assert client.get('/auth/me', headers=auth(me.json())).status_code == 200
    assert join(client, joined, owner).status_code == 400


def test_admin_creation_requires_system_admin_and_member_cannot_read_admin_data(accounts):
    client, _, root, owner, member, _ = accounts
    assert client.post('/api/v1/admin/organizations', json={'name': 'Anonymous'}).status_code == 401
    for account in (member, owner):
        assert client.post('/api/v1/admin/organizations', headers=auth(account), json={'name': 'Denied'}).status_code == 403
    result = client.post('/api/v1/admin/organizations', headers=auth(root), json={'name': 'System-created'})
    assert result.status_code == 200
    join(client, member, owner)
    for path in ('/users', '/organizations', f"/organizations/{owner['organization_id']}/users"):
        assert client.get('/api/v1/admin' + path, headers=auth(member)).status_code == 403


def test_deactivation_is_visible_and_blocks_existing_token_and_login(accounts):
    client, _, root, owner, member, _ = accounts
    join(client, member, owner)
    path = f"/api/v1/admin/users/{member['user_id']}"
    updated = client.patch(path, headers=auth(owner), json={'is_active': False, 'nickname': 'Saved member'})
    assert updated.status_code == 200 and updated.json()['is_active'] is False
    assert client.get(path, headers=auth(owner)).json()['is_active'] is False
    for listing in ('/api/v1/admin/users', f"/api/v1/admin/organizations/{owner['organization_id']}/users"):
        items = client.get(listing, headers=auth(owner)).json()
        item = next(item for item in items if item['id'] == member['user_id'])
        assert item['is_active'] is False and item['nickname'] == 'Saved member'
    assert client.get('/auth/me', headers=auth(member)).status_code == 401
    assert client.post('/auth/login', json={'email': 'member@example.invalid', 'password': PASSWORD}).status_code == 403
    assert client.patch(path, headers=auth(root), json={'is_active': True}).status_code == 200
    login = client.post('/auth/login', json={'email': 'member@example.invalid', 'password': PASSWORD})
    assert login.status_code == 200 and client.get('/auth/me', headers=auth(login.json())).status_code == 200


def test_cross_org_admin_cannot_read_edit_or_remove_other_members(accounts):
    client, _, root, owner, member, register = accounts
    outsider = register('other-owner')
    response = client.post('/auth/organization/create', headers=auth(outsider), json={'name': 'Other Company'})
    other = response.json()
    join(client, member, owner)
    user_path = f"/api/v1/admin/users/{member['user_id']}"
    assert client.get(user_path, headers=auth(other)).status_code == 403
    assert client.patch(user_path, headers=auth(other), json={'nickname': 'Wrong tenant'}).status_code == 403
    assert client.delete(f"/api/v1/admin/organizations/{owner['organization_id']}/users/{member['user_id']}", headers=auth(other)).status_code == 403
    assert {item['id'] for item in client.get('/api/v1/admin/organizations', headers=auth(other)).json()} == {other['organization_id']}
    assert client.patch(user_path, headers=auth(owner), json={'role': 'admin'}).status_code == 403
    assert client.patch(f"/api/v1/admin/users/{owner['user_id']}", headers=auth(owner), json={'is_active': False}).status_code == 400


def test_role_transfer_and_removal_take_effect_for_existing_tokens(accounts):
    client, _, root, owner, member, _ = accounts
    join(client, member, owner)
    org = owner['organization_id']
    assert client.post(f'/api/v1/admin/organizations/{org}/admin', headers=auth(owner), json={'user_id': member['user_id']}).status_code == 200
    assert client.get('/api/v1/admin/users', headers=auth(owner)).status_code == 403
    assert client.get('/api/v1/admin/users', headers=auth(member)).status_code == 200
    assert client.delete(f"/api/v1/admin/organizations/{org}/users/{member['user_id']}", headers=auth(member)).status_code == 400
    assert client.delete(f"/api/v1/admin/organizations/{org}/users/{owner['user_id']}", headers=auth(member)).status_code == 200
    me = client.get('/auth/me', headers=auth(owner)).json()
    assert me['organization_id'] is None and me['role'] == 'user'


def test_enterprise_admin_cannot_demote_system_admin_or_assign_disabled_user(accounts):
    client, factory, root, owner, member, _ = accounts
    org = owner['organization_id']
    # Place the system administrator in this organization without altering its role.
    with factory() as db:
        db.get(User, root['user_id']).organization_id = org
        db.get(User, member['user_id']).organization_id = org
        db.get(User, member['user_id']).is_active = False
        db.commit()
    assert client.post(f'/api/v1/admin/organizations/{org}/admin', headers=auth(owner), json={'user_id': root['user_id']}).status_code == 403
    assert client.delete(f"/api/v1/admin/organizations/{org}/users/{root['user_id']}", headers=auth(owner)).status_code == 403
    assert client.post(f'/api/v1/admin/organizations/{org}/admin', headers=auth(owner), json={'user_id': member['user_id']}).status_code == 400
    assert client.get('/auth/me', headers=auth(root)).json()['role'] == 'admin'


def test_expired_and_disabled_sessions_are_rejected_without_database_writes(accounts):
    client, factory, root, _, _, _ = accounts
    token = create_access_token({'user_id': root['user_id'], 'role': 'admin'}, timedelta(seconds=-1))
    assert client.post('/api/v1/admin/organizations', headers={'Authorization': 'Bearer ' + token}, json={'name': 'Expired'}).status_code == 401
    with factory() as db:
        db.get(User, root['user_id']).is_active = False
        db.commit()
    assert client.post('/api/v1/admin/organizations', headers=auth(root), json={'name': 'Disabled'}).status_code == 401


@pytest.mark.parametrize('action', ['create', 'join'])
def test_system_admin_keeps_system_role_when_obtaining_membership(accounts, action):
    client, _, root, owner, _, _ = accounts
    response = (join(client, root, owner) if action == 'join' else
                client.post('/auth/organization/create', headers=auth(root), json={'name': 'System membership'}))
    assert response.status_code == 200 and response.json()['role'] == 'admin'
    assert client.get('/api/v1/admin/users', headers=auth(response.json())).status_code == 200


def test_profile_fields_round_trip_and_duplicate_email_does_not_corrupt_profile(accounts):
    client, _, _, _, member, _ = accounts
    me = client.get('/auth/me', headers=auth(member)).json()
    assert me['id'] == member['user_id'] and me['email'] == 'member@example.invalid'
    assert not me['is_wechat_bound']
    update = {'nickname': 'Saved profile', 'email': ' UPDATED@EXAMPLE.INVALID ', 'phone': '00000000000', 'bio': 'Synthetic acceptance profile'}
    assert client.patch('/auth/profile', headers=auth(member), json=update).status_code == 200
    restored = client.get('/auth/me', headers=auth(member)).json()
    for key in ('nickname', 'phone', 'bio'):
        assert restored[key] == update[key]
    assert restored['email'] == 'updated@example.invalid'
    duplicate = client.patch('/auth/profile', headers=auth(member), json={'email': 'owner@example.invalid', 'nickname': 'Must not save'})
    assert duplicate.status_code == 409
    restored = client.get('/auth/me', headers=auth(member)).json()
    assert restored['email'] == 'updated@example.invalid' and restored['nickname'] == 'Saved profile'
    assert client.post('/auth/login', json={'email': 'updated@example.invalid', 'password': PASSWORD}).status_code == 200
    assert client.patch('/auth/profile', headers=auth(member), json={'email': ''}).status_code == 400


def test_legacy_create_uses_same_membership_rules_and_routes_are_unambiguous(accounts):
    client, _, root, _, _, _ = accounts
    result = client.post('/auth/organization', headers=auth(root), json={'name': 'Legacy entry'})
    assert result.status_code == 201 and result.json()['role'] == 'admin'
    assert client.get('/auth/me', headers=auth(result.json())).status_code == 200
    routes = [(method, route.path) for route in auth_router.router.routes for method in route.methods]
    assert len(routes) == len(set(routes))
