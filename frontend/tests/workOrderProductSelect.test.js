import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import { searchWorkOrderProducts, workOrderProductLabel } from '../src/utils/workOrderProductPicker.js';

const source = readFileSync(new URL('../src/components/admin/WorkOrderProductSelect.vue', import.meta.url), 'utf8');
const script = source.match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/^import .*;$/gm, '');

function harness(pointerType = 'touch') {
  const product = { id: 12, name: '機油', retail_price: 350 };
  const props = { products: [product], modelValue: null, disabled: false };
  const calls = [];
  const context = vm.createContext({
    defineProps: () => props,
    defineEmits: () => (name, id) => { calls.push([name, id]); props.modelValue = id; },
    ref: value => ({ value }), computed: getter => ({ get value() { return getter(); } }),
    watch: () => {}, useId: () => 'test-product', nextTick: async () => {},
    searchWorkOrderProducts, workOrderProductLabel,
  });
  vm.runInContext(script, context);
  let hit;
  const option = { ownerDocument: { elementFromPoint: () => hit }, contains: node => node === option };
  hit = option;
  const event = extra => ({
    pointerType, pointerId: 1, isPrimary: true, button: 0,
    clientX: 10, clientY: 10, currentTarget: option, preventDefault() {}, ...extra,
  });
  context.show();
  return { context, calls, product, event, setHit: value => { hit = value; },
    label: () => vm.runInContext('selectedLabel.value', context),
    isOpen: () => vm.runInContext('open.value', context) };
}

test('touch and pen taps select the product without a synthesized click and retain its label', () => {
  for (const pointerType of ['touch', 'pen']) {
    const h = harness(pointerType);
    h.context.startOptionPointer(h.event());
    h.context.finishOptionPointer(h.event(), h.product);
    assert.deepEqual(h.calls, [['select', 12]]);
    assert.equal(h.isOpen(), false);
    assert.equal(h.label(), '機油');
  }
});

test('scrolling, canceled touches and releases outside the option do not select', () => {
  for (const scenario of ['move', 'release-move', 'cancel', 'outside', 'secondary', 'mismatched']) {
    const h = harness();
    h.context.startOptionPointer(h.event({ isPrimary: scenario !== 'secondary' }));
    if (scenario === 'move') {
      h.context.moveOptionPointer(h.event({ clientY: 40 }));
      h.context.moveOptionPointer(h.event());
    }
    if (scenario === 'cancel') h.context.cancelOptionPointer();
    if (scenario === 'outside') h.setHit({});
    h.context.finishOptionPointer(h.event({
      clientY: scenario === 'release-move' ? 40 : 10,
      pointerId: scenario === 'mismatched' ? 2 : 1,
    }), h.product);
    assert.equal(h.calls.length, 0, scenario);
    assert.equal(h.isOpen(), true, scenario);
  }
});

test('mouse selection uses click and keyboard selection uses Enter', () => {
  const h = harness('mouse');
  h.context.startOptionPointer(h.event());
  h.context.finishOptionPointer(h.event(), h.product);
  assert.equal(h.calls.length, 0);
  h.context.select(h.product);
  assert.deepEqual(h.calls, [['select', 12]]);

  const keyboard = harness();
  vm.runInContext('activeIndex.value = 0', keyboard.context);
  keyboard.context.confirm({ preventDefault() {}, isComposing: true });
  assert.equal(keyboard.calls.length, 0);
  keyboard.context.confirm({ preventDefault() {}, isComposing: false });
  assert.deepEqual(keyboard.calls, [['select', 12]]);
});
