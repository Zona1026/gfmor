import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies.admin_auth import require_admin
from api.endpoints import accident_estimates
from db.database import get_db
from db.models import AccidentEstimate


class AccidentEstimateTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        AccidentEstimate.__table__.create(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.app = FastAPI()
        self.app.include_router(accident_estimates.router, prefix='/estimates')
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.app.dependency_overrides[require_admin] = lambda: {'is_admin': True}
        self.payload = dict(customer_name='測試客戶', phone='0912345678', license_plate='ABC-123',
                            estimate_date='2026-10-21', opened_date='2026-10-21', labor=800,
                            items=[dict(name='後照鏡', quantity=2, unit_price=1250, freight=100,
                                        unit='個', internal_note='PRIVATE-PART-NUMBER')],
                            internal_note='PRIVATE-STORE-NOTE')

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def request(self, method, path='/estimates/', payload=None):
        from urllib.parse import urlsplit
        parsed = urlsplit(path)
        body = json.dumps(payload).encode() if payload is not None else b''
        messages = []

        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}

        async def send(message):
            messages.append(message)

        scope = dict(type='http', asgi={'version': '3.0'}, http_version='1.1', method=method,
                     scheme='http', path=parsed.path, raw_path=parsed.path.encode(),
                     query_string=parsed.query.encode(), root_path='', client=('test', 1),
                     server=('test', 80), headers=[(b'content-type', b'application/json')])
        asyncio.run(self.app(scope, receive, send))
        status = next(m['status'] for m in messages if m['type'] == 'http.response.start')
        content = b''.join(m.get('body', b'') for m in messages if m['type'] == 'http.response.body')
        return SimpleNamespace(status=status, data=json.loads(content))

    def test_save_reload_update_and_server_calculated_totals(self):
        self.payload['total'] = 1
        self.payload['items'][0]['subtotal'] = 1
        created = self.request('POST', payload=self.payload)
        self.assertEqual(created.status, 201)
        self.assertEqual(created.data['total'], 3400)
        self.assertEqual(created.data['items'][0]['subtotal'], 2600)
        stored = self.db.get(AccidentEstimate, created.data['id'])
        self.assertNotIn('subtotal', stored.items[0])
        self.db.expire_all()
        loaded = self.request('GET', f"/estimates/{created.data['id']}")
        self.assertEqual(loaded.data['internal_note'], 'PRIVATE-STORE-NOTE')
        self.assertEqual(loaded.data['items'][0]['internal_note'], 'PRIVATE-PART-NUMBER')
        self.payload['items'][0]['quantity'] = 3
        updated = self.request('PUT', f"/estimates/{created.data['id']}", self.payload)
        self.assertEqual(updated.status, 200)
        self.assertEqual(updated.data['total'], 4650)
        self.assertEqual(self.request('GET', '/estimates/?q=ABC').data[0]['total'], 4650)
        self.assertEqual(self.request('GET', '/estimates/?q=absent').data, [])
        self.assertEqual(self.request('GET', '/estimates/?q=%25').data, [])

    def test_authentication_required_for_every_endpoint(self):
        self.app.dependency_overrides.pop(require_admin)
        for method, path in [('GET', '/estimates/'), ('GET', '/estimates/1'), ('POST', '/estimates/'), ('PUT', '/estimates/1')]:
            self.assertEqual(self.request(method, path, self.payload).status, 401)

    def test_validation_does_not_persist_bad_amounts(self):
        for field, value in [('unit_price', -1), ('freight', -1), ('quantity', 0), ('quantity', 1.5), ('unit_price', 1.5)]:
            with self.subTest(field=field, value=value):
                payload = json.loads(json.dumps(self.payload))
                payload['items'][0][field] = value
                self.assertEqual(self.request('POST', payload=payload).status, 422)
        self.assertEqual(self.db.query(AccidentEstimate).count(), 0)
        self.assertEqual(self.request('GET', '/estimates/999').status, 404)
        self.assertEqual(self.request('PUT', '/estimates/999', self.payload).status, 404)

    def test_empty_items_labor_only_and_large_estimates(self):
        self.payload['items'] = []
        self.assertEqual(self.request('POST', payload=self.payload).data['total'], 800)
        self.payload['items'] = [dict(name=f'零件 {index}', quantity=1, unit_price=10) for index in range(40)]
        created = self.request('POST', payload=self.payload)
        self.assertEqual(len(created.data['items']), 40)
        self.assertEqual(created.data['total'], 1200)

    def test_migration_upgrade_and_downgrade(self):
        path = Path(__file__).parents[1] / 'migrations/versions/20261021_0031_accident_estimates.py'
        spec = importlib.util.spec_from_file_location('estimate_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine('sqlite://')
        try:
            with engine.begin() as connection:
                with Operations.context(MigrationContext.configure(connection)):
                    migration.upgrade()
                    self.assertEqual(set(c['name'] for c in inspect(connection).get_columns('accident_estimates')),
                                     set(AccidentEstimate.__table__.columns.keys()))
                    migration.downgrade()
                    self.assertFalse(inspect(connection).has_table('accident_estimates'))
        finally:
            engine.dispose()


if __name__ == '__main__':
    unittest.main()
