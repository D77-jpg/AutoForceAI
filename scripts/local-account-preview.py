"""Disposable account/organization browser fixture; never loads production .env.

Run with the digital-brain virtualenv. Point the temporary 3051 console to 8011.
All users, passwords and invite codes here belong only to this temporary database.
No external model calls, CRM dispatcher, email or publishing workers are started.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile

SERVICE = Path(__file__).resolve().parents[1] / 'services' / 'digital-brain'


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8011)
    parser.add_argument('--check-only', action='store_true', help='Create/check the fixture, then clean up and exit')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='afai-account-preview-') as temporary:
        database_url = 'sqlite:///' + (Path(temporary) / 'accounts.db').as_posix()
        os.environ['DATABASE_URL'] = database_url
        os.environ['PYTHON_DOTENV_DISABLED'] = '1'
        os.environ['JWT_SECRET'] = secrets.token_urlsafe(48)
        os.environ['APP_ENV'] = 'development'
        os.environ['ALLOW_EMAIL_REGISTER'] = 'true'
        os.environ['CRM_BACKGROUND_WORKER_ENABLED'] = '0'
        os.chdir(SERVICE)
        sys.path.insert(0, str(SERVICE))
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from core.db_manager import SHARED_ENGINE
        from database.base import Base
        from database import models
        from routers import auth_router, admin_router, platform_router, agent_router
        import uvicorn
        assert (SHARED_ENGINE.dialect.name == 'sqlite'
                and Path(SHARED_ENGINE.url.database).resolve() == (Path(temporary) / 'accounts.db').resolve()), 'Refusing to use a non-fixture database'
        Base.metadata.create_all(SHARED_ENGINE)
        app = FastAPI()
        for module in (auth_router, admin_router, platform_router, agent_router):
            app.include_router(module.router)
        password = 'Local-Account-Acceptance!2026'
        try:
            with TestClient(app) as client:
                accounts = {}
                for name in ('system', 'owner', 'member'):
                    response = client.post('/auth/register', json={
                        'email': f'{name}@acceptance.invalid', 'password': password,
                        'nickname': '验收-' + name,
                    })
                    assert response.status_code == 201
                    accounts[name] = response.json()
                response = client.post('/auth/organization/create',
                    headers={'Authorization': 'Bearer ' + accounts['owner']['access_token']},
                    json={'name': '本地组织验收-20261007'})
                assert response.status_code == 200
                organization = response.json()
                # Only disposable fixture access details; never emit JWTs.
                print(json.dumps({'fixture_only': True, 'organization': organization['organization_name'],
                                  'invite_code': organization['invite_code'],
                                  'emails': [name + '@acceptance.invalid' for name in accounts]}, ensure_ascii=False), flush=True)
            if not args.check_only:
                uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning')
        finally:
            SHARED_ENGINE.dispose()


if __name__ == '__main__':
    run()
