import assert from 'node:assert/strict';
import test from 'node:test';
import { moveLineItem, promotionLineKey, mergePromotionGifts } from '../src/utils/workOrderLineOrder.js';

test('moving rows retains each item and its data and respects boundaries', () => {
  const first = { id: 1, name: 'First', quantity: 2 };
  const second = { id: 2, name: 'Second', quantity: 3 };
  const items = [first, second];
  moveLineItem(items, 0, -1);
  moveLineItem(items, 1, 1);
  assert.deepEqual(items, [first, second]);
  moveLineItem(items, 1, -1);
  assert.equal(items[0], second);
  assert.equal(items[1], first);
  assert.equal(items[0].quantity, 3);
  moveLineItem(items, 0, 1);
  assert.deepEqual(items, [first, second]);
});

test('reordering does not trigger promotion quotes but quantity changes do', () => {
  const items = [{ product_id: 1, type: 'PART', quantity: 2 }, { product_id: 2, type: 'PART', quantity: 1 }];
  const key = promotionLineKey(items);
  moveLineItem(items, 0, 1);
  assert.equal(promotionLineKey(items), key);
  items[0].quantity++;
  assert.notEqual(promotionLineKey(items), key);
});

test('promotion refresh keeps moved gifts in place, removes expired gifts and appends new gifts', () => {
  const first = { id: 1, product_id: 1 };
  const second = { id: 2, product_id: 2 };
  const gift = { id: 3, promotion_gift_id: 10, product_id: 3, quantity: 1 };
  const expired = { promotion_gift_id: 20, product_id: 4 };
  const newGift = { promotion_gift_id: 30, product_id: 5 };
  const result = mergePromotionGifts([gift, first, expired, second], [{ ...gift, quantity: 2 }, newGift]);
  assert.equal(result[0].id, 3);
  assert.equal(result[0].quantity, 2);
  assert.equal(result[1], first);
  assert.equal(result[2], second);
  assert.equal(result[3], newGift);
  assert.equal(result.length, 4);
});
