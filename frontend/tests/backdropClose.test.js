import assert from 'node:assert/strict';
import test from 'node:test';
import backdropClose from '../src/directives/backdropClose.js';

function harness() {
  const listeners = new Map();
  const dialog = {};
  let hit;
  let closed = 0;
  const el = {
    ownerDocument: { elementFromPoint: () => hit },
    addEventListener: (name, handler) => listeners.set(name, handler),
    removeEventListener: (name, handler) => {
      assert.equal(listeners.get(name), handler);
      listeners.delete(name);
    },
  };
  backdropClose.mounted(el, { value: () => closed++ });
  const fire = (name, target, extra = {}) => listeners.get(name)({
    target, pointerId: 1, button: 0, isPrimary: true, clientX: 0, clientY: 0, ...extra,
  });
  const gesture = (start, end, clickTarget = el) => {
    fire('pointerdown', start);
    hit = end;
    fire('pointerup', end);
    fire('click', clickTarget);
  };
  return { el, dialog, fire, gesture, listeners, setHit: value => { hit = value; }, get closed() { return closed; } };
}

test('dragging from dialog to backdrop preserves the modal and a subsequent backdrop click closes it', () => {
  const h = harness();
  h.gesture(h.dialog, h.el);
  assert.equal(h.closed, 0);
  h.gesture(h.el, h.el);
  assert.equal(h.closed, 1);
});

test('dragging from backdrop to dialog and clicking within dialog preserve the modal', () => {
  const h = harness();
  h.gesture(h.el, h.dialog);
  h.gesture(h.dialog, h.dialog, h.dialog);
  assert.equal(h.closed, 0);
});

test('touch capture cannot close the modal when the finger ends over its content', () => {
  const h = harness();
  h.fire('pointerdown', h.el);
  h.setHit(h.dialog);
  h.fire('pointerup', h.el);
  h.fire('click', h.el);
  assert.equal(h.closed, 0);
});

test('canceled, secondary and mismatched pointer gestures do not close the modal', () => {
  const h = harness();
  h.setHit(h.el);
  h.fire('pointerdown', h.el);
  h.fire('pointercancel', h.el);
  h.fire('pointerup', h.el);
  h.fire('click', h.el);
  h.fire('pointerdown', h.el, { button: 2 });
  h.fire('pointerup', h.el);
  h.fire('click', h.el);
  h.fire('pointerdown', h.el, { isPrimary: false });
  h.fire('pointerup', h.el);
  h.fire('click', h.el);
  h.fire('pointerdown', h.el);
  h.fire('pointerup', h.el, { pointerId: 2 });
  h.fire('click', h.el);
  assert.equal(h.closed, 0);
});

test('updated callbacks are used and all listeners are removed on unmount', () => {
  const h = harness();
  let updatedClosed = 0;
  backdropClose.updated(h.el, { value: () => updatedClosed++ });
  h.gesture(h.el, h.el);
  assert.equal(h.closed, 0);
  assert.equal(updatedClosed, 1);
  backdropClose.unmounted(h.el);
  assert.equal(h.listeners.size, 0);
});
