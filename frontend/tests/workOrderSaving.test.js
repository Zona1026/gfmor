import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import { setImmediate } from 'node:timers/promises';

const source = readFileSync(new URL('../src/views/admin/WorkOrders.vue', import.meta.url), 'utf8');
const sortSave = source.slice(source.indexOf('const saveLineOrder ='), source.indexOf('const addCreateLineItem ='));
const orderSave = source.slice(source.indexOf('const saveWorkOrder ='), source.indexOf('const submitPayment ='));
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};

function harness() {
  const request = deferred();
  const alerts = [];
  const calls = [];
  const ref = value => ({ value });
  const context = vm.createContext({
    selectedWorkOrder: ref({ id: 42 }), canSaveLineOrder: ref(true),
    saving: ref(false), detailLoading: ref(false), detailForm: ref({ notes: 'Note' }),
    detailLineItems: ref([{ id: 3 }, { id: 1 }, { id: 2 }]),
    supervisorReviewLocked: ref(true), membershipSelectionLocked: ref(true),
    originalDetailRedeemedPoints: ref(0),
    normalizeWorkOrderResponsibleStaff: value => value,
    getErrorMessage: error => error.message, alert: message => alerts.push(message),
    fetchWorkOrders: async () => {}, fetchDetailVehicleOptions: async () => {},
    staffNameById: () => 'Staff', showRewardQrIfOilItems: () => false,
    updateWorkOrder: (id, payload) => { calls.push(['update', id, payload]); return request.promise; },
    reorderWorkOrderLineItems: (id, ids) => { calls.push(['order', id, [...ids]]); return request.promise; },
  });
  vm.runInContext(`let detailRequestId = 0;
    ${sortSave} ${orderSave}
    globalThis.saveSort = saveLineOrder;
    globalThis.saveOrder = saveWorkOrder;
    globalThis.switchOrder = value => { detailRequestId++; selectedWorkOrder.value = value; };`, context);
  return { context, request, alerts, calls };
}

test('saving only the order uses all original IDs and leaves unsaved edits intact', async () => {
  const h = harness();
  h.context.detailLineItems.value[0].name = 'Unsaved edit';
  const pending = h.context.saveSort();
  h.request.resolve({ id: 42, line_items: [{ id: 3 }, { id: 1 }, { id: 2 }] });
  await pending;
  assert.deepEqual(h.calls, [['order', 42, [3, 1, 2]]]);
  assert.equal(h.context.detailLineItems.value[0].name, 'Unsaved edit');
  assert.equal(h.context.saving.value, false);
});

for (const action of ['saveSort', 'saveOrder']) {
  for (const replacement of [null, { id: 43 }]) {
    test(`${action} cannot restore a closed order or replace a different order (${replacement?.id || 'closed'})`, async () => {
      const h = harness();
      const pending = h.context[action]();
      h.context.switchOrder(replacement);
      h.context.detailLineItems.value = [{ id: 99 }];
      h.context.supervisorReviewLocked.value = false;
      h.request.resolve({ id: 42, line_items: [] });
      await pending;
      assert.equal(h.context.selectedWorkOrder.value?.id, replacement?.id);
      assert.equal(h.context.detailLineItems.value[0].id, 99);
      assert.deepEqual(h.alerts, []);
      assert.equal(h.context.saving.value, false);
      const sortingCall = h.calls.find(call => call[0] === 'order');
      assert.equal(sortingCall[1], 42);
      assert.deepEqual(sortingCall[2], [3, 1, 2]);
    });
  }

  test(`${action} suppresses errors from an order that has been closed`, async () => {
    const h = harness();
    const pending = h.context[action]();
    h.context.switchOrder(null);
    h.request.reject(new Error('Connection failed'));
    await pending;
    assert.deepEqual(h.alerts, []);
    assert.equal(h.context.saving.value, false);
  });
}

test('closing the order during the list refresh does not show a stale success alert', async () => {
  const h = harness();
  const refresh = deferred();
  h.context.fetchWorkOrders = () => refresh.promise;
  const pending = h.context.saveSort();
  h.request.resolve({ id: 42 });
  await setImmediate();
  h.context.switchOrder(null);
  refresh.resolve();
  await pending;
  assert.deepEqual(h.alerts, []);
});
