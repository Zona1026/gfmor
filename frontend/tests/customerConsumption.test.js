import test from 'node:test';
import assert from 'node:assert/strict';
import { buildConsumptionRecords } from '../src/utils/customerConsumption.js';
import { productDetailsForm, appendProductDetails } from '../src/utils/productDetails.js';

test('consumption history includes unpaid work orders and mall orders, without duplicating split payments', () => {
  const result = buildConsumptionRecords({
    service_records: [
      { work_order_id: 21, total_amount: 2500, created_at: '2026-10-10', payment_status: 'PAID', vehicle_license_plate: 'NQX-2056' },
      { work_order_id: 19, total_amount: 1800, created_at: '2026-10-07', payment_status: 'UNPAID' }
    ],
    spending_records: [
      { id: 'pay-1', source: 'work_order_payment', source_id: 21, amount: 1000, method: '現金' },
      { id: 'pay-2', source: 'work_order_payment', source_id: 21, amount: 1500, method: '轉帳' },
      { id: 'order-5', source: 'order', source_id: 5, amount: 500, status: 'DEPOSIT_PAID', created_at: '2026-10-09' }
    ]
  });
  assert.equal(result.length, 3);
  assert.deepEqual(result.map(row => row.source_id), [21, 5, 19]);
  assert.equal(result[0].amount, 2500);
  assert.equal(result[0].vehicle_license_plate, 'NQX-2056');
  assert.equal(result[0].method, '現金、轉帳');
  assert.equal(result[1].payment_status, 'PARTIALLY_PAID');
  assert.equal(result[2].payment_status, 'UNPAID');
  assert.deepEqual(buildConsumptionRecords(null), []);
});

test('multiple vehicle models round trip through product forms and can be cleared', () => {
  const form = productDetailsForm({ vehicle_model: 'JET SL' });
  assert.deepEqual(form.vehicle_models, ['JET SL']);
  form.vehicle_models.push('勁戰六代');
  const data = new FormData();
  appendProductDetails(data, form);
  const metadata = JSON.parse(data.get('product_metadata'));
  assert.deepEqual(metadata.vehicle_models, ['JET SL', '勁戰六代']);
  assert.deepEqual(productDetailsForm(metadata).vehicle_models, metadata.vehicle_models);
  form.vehicle_models = [];
  const cleared = new FormData();
  appendProductDetails(cleared, form);
  assert.deepEqual(JSON.parse(cleared.get('product_metadata')).vehicle_models, []);
  assert.equal(JSON.parse(cleared.get('product_metadata')).vehicle_model, null);
});
