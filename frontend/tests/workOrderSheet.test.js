import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import { summarizeWorkOrder } from '../src/utils/workOrderAmounts.js';

const source = readFileSync(new URL('../src/views/admin/WorkOrders.vue', import.meta.url), 'utf8');
const actions = source.slice(source.indexOf('const addQuickProduct ='), source.indexOf('watch([showCreateModal, selectedWorkOrder]'));
function harness() {
  const ref = value => ({ value });
  const alerts = [];
  let saved = 0;
  const context = vm.createContext({
    quickProductTarget: ref('create'), saving: ref(false), showCreateModal: ref(true),
    canCreateWorkOrder: ref(true), canEditWorkOrder: ref(true), canManageWorkOrderPayments: ref(true),
    selectedWorkOrder: ref({ id: 42, status: 'INSPECTION_PENDING', paid_amount: 500 }), detailForm: ref({ status: 'INSPECTION_PENDING' }),
    lineItemEditingLocked: ref(false), createMode: ref('normal'), createForm: ref({ award_points: false }),
    createLineItems: ref([{ type: 'SERVICE', name: '', quantity: 1 }]), detailLineItems: ref([]),
    detailTotal: ref(500), checkoutSection: ref(null),
    defaultLineItem: () => ({ type: 'SERVICE', name: '', quantity: 1, unit_price: 0, points_redeemed: 0, counts_toward_membership: true }),
    applyProductToLine: item => { item.name = 'Test product'; item.unit_price = 350; },
    hasBlockingApproval: () => false,
    alert: message => alerts.push(message),
    saveWorkOrder: async () => { saved++; context.selectedWorkOrder.value.status = 'COMPLETED'; },
  });
  vm.runInContext(`${actions}; globalThis.add = addQuickProduct; globalThis.complete = completeWorkOrder;`, context);
  return { context, alerts, get saved() { return saved; } };
}

test('sheet summary separates positive charges and all discounts, and clamps the payable total', () => {
  assert.deepEqual(summarizeWorkOrder([
    { type: 'PART', quantity: 2, unit_price: 350 }, { type: 'LABOR', quantity: 1, unit_price: 200 },
    { type: 'DISCOUNT', quantity: 1, unit_price: 50 }, { type: 'DISCOUNT', quantity: 2, unit_price: 25 },
  ]), { subtotal: 900, discount: 100, total: 800 });
  assert.deepEqual(summarizeWorkOrder([{ type: 'DISCOUNT', quantity: 1, unit_price: 500 }]), { subtotal: 0, discount: 500, total: 0 });
  assert.deepEqual(summarizeWorkOrder([]), { subtotal: 0, discount: 0, total: 0 });
});

test('quick add reuses a blank row, then keeps repeated products as separate lines', () => {
  const h = harness();
  h.context.add({ id: 12, inventory_type: 'BOTH' });
  h.context.add({ id: 12, inventory_type: 'PART' });
  const rows = h.context.createLineItems.value;
  assert.equal(rows.length, 2);
  assert.equal(rows[0].product_id, 12);
  assert.equal(rows[0].type, 'PART');
  assert.equal(rows[0].unit_price, 350);
  assert.equal(rows[0].quantity, 1);
  assert.notEqual(rows[0], rows[1]);
});

test('quick add supports labor, major maintenance and historical point eligibility', () => {
  for (const type of ['LABOR', 'MAJOR_MAINTENANCE']) {
    const h = harness();
    h.context.createMode.value = 'historical';
    h.context.add({ id: 12, inventory_type: type });
    assert.equal(h.context.createLineItems.value[0].type, type);
    assert.equal(h.context.createLineItems.value[0].counts_toward_membership, false);
  }
});

test('quick add cannot modify closed, unauthorized or reviewed orders', () => {
  for (const condition of ['closed', 'permission', 'reviewed', 'busy']) {
    const h = harness();
    h.context.quickProductTarget.value = 'detail';
    if (condition === 'closed') h.context.selectedWorkOrder.value = null;
    if (condition === 'permission') h.context.canEditWorkOrder.value = false;
    if (condition === 'reviewed') h.context.lineItemEditingLocked.value = true;
    if (condition === 'busy') h.context.saving.value = true;
    h.context.add({ id: 12, inventory_type: 'PART' });
    assert.equal(h.context.detailLineItems.value.length, 0, condition);
  }
});

test('closing an unpaid order opens payment controls without registering a payment or changing status', async () => {
  const h = harness();
  let focused = false;
  h.context.detailTotal.value = 600;
  h.context.checkoutSection.value = { open: false, scrollIntoView() {}, querySelector: () => ({ focus: () => { focused = true; } }) };
  await h.context.complete();
  assert.equal(h.saved, 0);
  assert.equal(h.context.detailForm.value.status, 'INSPECTION_PENDING');
  assert.equal(h.context.checkoutSection.value.open, true);
  assert.equal(focused, true);
});

test('closing requires approval and permission; paid and zero-total orders use the existing save flow', async () => {
  for (const reason of ['approval', 'permission', 'busy']) {
    const h = harness();
    if (reason === 'approval') h.context.hasBlockingApproval = () => true;
    if (reason === 'permission') h.context.canManageWorkOrderPayments.value = false;
    if (reason === 'busy') h.context.saving.value = true;
    await h.context.complete();
    assert.equal(h.saved, 0);
  }
  for (const total of [0, 500]) {
    const h = harness();
    h.context.detailTotal.value = total;
    await h.context.complete();
    assert.equal(h.saved, 1);
    assert.equal(h.context.selectedWorkOrder.value.status, 'COMPLETED');
  }
});

test('a failed closing restores the previous editor status', async () => {
  const h = harness();
  h.context.saveWorkOrder = async () => {};
  await h.context.complete();
  assert.equal(h.context.detailForm.value.status, 'INSPECTION_PENDING');
});
