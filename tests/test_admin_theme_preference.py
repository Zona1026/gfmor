from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from jose import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.endpoints import admin
from core.config import settings
from core.security import get_password_hash
from db import models, database
from test_product_pricing_fields import ASGIClient


class AdminThemePreferenceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.db.add_all([models.Admin(username='staff', role='一般', hashed_password=get_password_hash('test-password')),
                         models.Admin(username='manager', role='管理層', hashed_password='unused'),
                         models.Admin(username='super', role='最高級', hashed_password='unused')])
        self.db.commit()
        app = FastAPI()
        app.include_router(admin.router, prefix='/admin')
        app.dependency_overrides[database.get_db] = lambda: self.db
        self.client = ASGIClient(app)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def headers(self, username='staff', token_role='admin'):
        token = jwt.encode({'sub': username, 'role': token_role,
                            'admin_role': {'staff': '一般', 'manager': '管理層', 'super': '最高級'}.get(username, '一般'),
                            'exp': datetime.now(timezone.utc) + timedelta(minutes=5)},
                           settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return {'Authorization': f'Bearer {token}'}

    def request(self, method='GET', data=None, username='staff', headers=None):
        return self.client.request(method, '/admin/me/preferences', headers=headers if headers is not None else self.headers(username), json_data=data)

    def test_all_admin_roles_can_change_only_their_own_preference(self):
        for username in ('staff', 'manager', 'super'):
            self.assertEqual(self.request(username=username).data, {'theme': 'dark'})
            response = self.request('PATCH', {'theme': 'light'}, username=username)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data, {'theme': 'light'})
        self.request('PATCH', {'theme': 'dark'}, username='staff')
        self.assertEqual(self.request(username='manager').data, {'theme': 'light'})
        self.assertEqual(self.request().data, {'theme': 'dark'})

    def test_invalid_or_unrelated_updates_do_not_change_preferences_or_permissions(self):
        for data in ({'theme': 'system'}, {'theme': None}, {}, {'theme': 'light', 'username': 'manager'},
                     {'theme': 'light', 'role': '最高級'}):
            self.assertEqual(self.request('PATCH', data).status_code, 422)
        staff = self.db.query(models.Admin).filter_by(username='staff').one()
        self.assertEqual((staff.theme_preference, staff.role), ('dark', '一般'))

    def test_authentication_is_required_and_missing_accounts_are_rejected(self):
        for headers in ({}, self.headers(token_role='member'), self.headers(username='deleted')):
            for method, data in [('GET', None), ('PATCH', {'theme': 'light'})]:
                self.assertEqual(self.request(method, data, headers=headers).status_code, 401)

    def test_login_returns_saved_preference_for_another_browser(self):
        self.request('PATCH', {'theme': 'light'})
        response = self.client.request('POST', '/admin/login', json_data={'username': 'staff', 'password': 'test-password'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['theme_preference'], 'light')

    def test_migration_preserves_old_accounts_and_initializes_dark(self):
        self.db.close()
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261124_0038_admin_theme_preference.py'
        spec = importlib.util.spec_from_file_location('admin_theme_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.engine.begin() as connection:
            with patch.object(migration, 'op', Operations(MigrationContext.configure(connection))):
                migration.downgrade()
                migration.upgrade()
            rows = connection.execute(text('SELECT username, role, theme_preference FROM admins ORDER BY username')).all()
            self.assertEqual(rows, [('manager', '管理層', 'dark'), ('staff', '一般', 'dark'), ('super', '最高級', 'dark')])
