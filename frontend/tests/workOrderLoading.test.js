import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import { setImmediate } from 'node:timers/promises';

const source = readFileSync(new URL('../src/views/admin/WorkOrders.vue', import.meta.url), 'utf8');
const openDetail = source.slice(source.indexOf('const openDetail ='), source.indexOf('const closeDetail ='));
const closeDetail = source.slice(source.indexOf('const closeDetail ='), source.indexOf('const saveWorkOrder ='));
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};

function harness() {
  const reads = new Map();
  const products = [];
  const alerts = [];
  const ref = value => ({ value });
  const context = vm.createContext({
    selectedWorkOrder: ref(null), detailLoading: ref(false), detailForm: ref({}),
    detailLineItems: ref([]), originalDetailRedeemedPoints: ref(0), paymentForm: ref({}),
    detailVehicleOptions: ref([]), detailVehicleId: ref(null), detailCustomerPoints: ref(0),
    getWorkOrder: id => { const pending = deferred(); reads.set(id, pending); return pending.promise; },
    normalizeWorkOrderResponsibleStaff: value => value,
    fetchProducts: () => { const pending = deferred(); products.push(pending); return pending.promise; },
    fetchStaffAdmins: async () => {}, fetchDetailVehicleOptions: async () => {},
    workOrderResponsibleStaffName: () => 'Staff', staffIdByName: () => 1,
    defaultResponsibleStaffId: () => 1, toDatetimeLocal: value => value,
    closeDeleteModal() {}, closeReopenModal() {}, closeRefundModal() {},
    alert: message => alerts.push(message), getErrorMessage: error => error.message,
    console: { error() {} }, authStore: { adminLogout() {} }, router: { push() {} },
  });
  vm.runInContext(`let detailRequestId = 0; ${openDetail} ${closeDetail}
    globalThis.open = openDetail; globalThis.close = closeDetail;`, context);
  return { context, reads, products, alerts };
}

test('closing the detail while related data loads does not show an error or restore the form', async () => {
  const h = harness();
  const pending = h.context.open(35);
  h.reads.get(35).resolve({ id: 35, service_type: 'REPAIR' });
  await setImmediate();
  h.context.close();
  h.products[0].resolve();
  await pending;
  assert.equal(h.context.selectedWorkOrder.value, null);
  assert.equal(h.context.detailLoading.value, false);
  assert.deepEqual(h.alerts, []);
  assert.equal(Object.keys(h.context.detailForm.value).length, 0);
});

test('an older response cannot replace the most recently opened work order', async () => {
  const h = harness();
  const old = h.context.open(35);
  const current = h.context.open(36);
  h.reads.get(36).resolve({ id: 36, service_type: 'MAINTENANCE', line_items: [] });
  await setImmediate();
  h.products[0].resolve();
  await current;
  h.reads.get(35).resolve({ id: 35, service_type: 'REPAIR' });
  await old;
  assert.equal(h.context.selectedWorkOrder.value.id, 36);
  assert.equal(h.context.detailForm.value.service_type, 'MAINTENANCE');
  assert.deepEqual(h.alerts, []);
});

test('an older related-data load cannot overwrite a newer form', async () => {
  const h = harness();
  const old = h.context.open(35);
  h.reads.get(35).resolve({ id: 35, service_type: 'REPAIR' });
  await setImmediate();
  const current = h.context.open(36);
  h.reads.get(36).resolve({ id: 36, service_type: 'MAINTENANCE', line_items: [] });
  await setImmediate();
  h.products[1].resolve();
  await current;
  h.products[0].resolve();
  await old;
  assert.equal(h.context.detailForm.value.service_type, 'MAINTENANCE');
  assert.deepEqual(h.alerts, []);
});

test('a current request failure still shows an error and ends loading', async () => {
  const h = harness();
  const pending = h.context.open(35);
  h.reads.get(35).reject(new Error('Connection failed'));
  await pending;
  assert.deepEqual(h.alerts, ['讀取工單失敗：Connection failed']);
  assert.equal(h.context.detailLoading.value, false);
});

test('late vehicle data cannot restore a closed work order selection', async () => {
  const pending = deferred();
  let current = true;
  const context = vm.createContext({
    detailVehicleId: { value: null }, detailVehicleOptions: { value: [] },
    detailCustomerPoints: { value: 0 },
    getCustomerDetail: () => pending.promise, console: { error() {} },
  });
  const vehicleLoader = source.slice(source.indexOf('const fetchDetailVehicleOptions ='),
    source.indexOf('const applyDetailVehicle ='));
  vm.runInContext(`${vehicleLoader} globalThis.load = fetchDetailVehicleOptions;`, context);
  const loading = context.load({ google_id: 'member', motor_id: 6 }, () => current);
  current = false;
  context.detailVehicleId.value = null;
  pending.resolve({ current_points: 100, vehicles: [{ id: 6 }] });
  await loading;
  assert.equal(context.detailVehicleId.value, null);
  assert.equal(context.detailVehicleOptions.value.length, 0);
  assert.equal(context.detailCustomerPoints.value, 0);
});

test('selecting a member vehicle prefills its current mileage, including zero', () => {
  const selectMemberMotor = source.slice(source.indexOf('const applySelectedMemberMotor ='),
    source.indexOf('const fetchDetailVehicleOptions ='));
  for (const mileage of [3500, 0, null]) {
    const context = vm.createContext({
      memberMotorOptions: { value: [{ key: 'member-6', user: { google_id: 'member' },
        motor: { id: 6, license_plate: 'TEST-001', mileage } }] },
      selectedMemberMotorKey: { value: 'member-6' }, createForm: { value: {} },
    });
    vm.runInContext(`${selectMemberMotor} applySelectedMemberMotor();`, context);
    assert.equal(context.createForm.value.vehicle_mileage, mileage);
    assert.equal(context.createForm.value.motor_id, 6);
  }
});
