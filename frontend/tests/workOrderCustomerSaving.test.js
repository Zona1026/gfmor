import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source = readFileSync(new URL('../src/components/admin/WorkOrderCustomerFields.vue', import.meta.url), 'utf8');
const save = source.match(/async function save\(\) \{[\s\S]*?\n\}/)[0];
function harness() {
  const calls = [], events = [];
  let resolve, reject;
  const response = new Promise((yes, no) => { resolve = yes; reject = no; });
  const ref = value => ({ value });
  const context = vm.createContext({
    props: { workOrder: { id: 155 }, disabled: false },
    name: ref('王先生'), phone: ref('0902103130'), changed: ref(true),
    saving: ref(false), error: ref(''), message: ref(''),
    updateWorkOrderCustomer: (id, payload) => { calls.push([id, payload]); return response; },
    emit: (event, saved) => events.push([event, saved]), nextTick: async () => {},
  });
  vm.runInContext(`let requestId = 0; ${save}; globalThis.save = save;`, context);
  return { context, calls, events, resolve, reject };
}

test('customer information saves independently and double clicks submit only once', async () => {
  const h = harness();
  const pending = h.context.save();
  await h.context.save();
  assert.equal(h.calls.length, 1);
  assert.equal(h.calls[0][0], 155);
  assert.equal(h.calls[0][1].name, '王先生');
  assert.equal(h.calls[0][1].phone, '0902103130');
  assert.deepEqual(Object.keys(h.calls[0][1]), ['name', 'phone']);
  const saved = { id: 155, customer_name: '王先生', customer_phone: '0902103130' };
  h.resolve(saved);
  await pending;
  assert.deepEqual(h.events, [['saved', saved]]);
  assert.equal(h.context.saving.value, false);
  assert.equal(h.context.message.value, '客人資訊已儲存。');
});

test('a failed customer save retains the entered name and telephone for retry', async () => {
  const h = harness();
  const pending = h.context.save();
  h.reject({ response: { data: { detail: '請重試' } } });
  await pending;
  assert.equal(h.context.name.value, '王先生');
  assert.equal(h.context.phone.value, '0902103130');
  assert.equal(h.context.error.value, '請重試');
  assert.equal(h.events.length, 0);
  assert.equal(h.context.saving.value, false);
});

test('a late save cannot replace another work order customer information', async () => {
  const h = harness();
  const pending = h.context.save();
  h.context.props.workOrder = { id: 156 };
  h.resolve({ id: 155, customer_name: 'Old order' });
  await pending;
  assert.equal(h.events.length, 0);
});

test('disabled, deleted or unchanged customer forms cannot submit', async () => {
  for (const reason of ['disabled', 'deleted', 'unchanged']) {
    const h = harness();
    if (reason === 'disabled') h.context.props.disabled = true;
    if (reason === 'deleted') h.context.props.workOrder.deleted_at = '2026-11-23';
    if (reason === 'unchanged') h.context.changed.value = false;
    await h.context.save();
    assert.equal(h.calls.length, 0);
  }
});
