import assert from 'node:assert/strict';
import test from 'node:test';
import { calculateMembershipTotal, calculateTotal, lineItemTotal } from '../src/utils/workOrderAmounts.js';

const charge = { type: 'SERVICE', quantity: 1, unit_price: 1000, counts_toward_membership: true };
const discount = { type: 'DISCOUNT', quantity: 1, unit_price: 200, counts_toward_membership: true };

test('a positive discount input shows a negative subtotal and reduces the bill once', () => {
  assert.equal(lineItemTotal(discount), -200);
  assert.equal(calculateTotal([charge, discount]), 800);
  assert.equal(calculateMembershipTotal([charge, discount]), 800);
});

test('changing the line type changes its contribution immediately', () => {
  const item = { ...discount, type: 'LABOR' };
  assert.equal(lineItemTotal(item), 200);
  assert.equal(calculateTotal([charge, item]), 1200);
  item.type = 'DISCOUNT';
  assert.equal(lineItemTotal(item), -200);
  assert.equal(calculateTotal([charge, item]), 800);
});

test('quantities and multiple discounts reduce the bill', () => {
  assert.equal(lineItemTotal({ ...discount, quantity: 2 }), -400);
  assert.equal(calculateTotal([charge, { ...discount, quantity: 2 }, discount]), 400);
});

test('discounts cannot make the payable or membership total negative', () => {
  assert.equal(calculateTotal([discount]), 0);
  const items = [charge, { ...discount, unit_price: 1500 }];
  assert.equal(calculateTotal(items), 0);
  assert.equal(calculateMembershipTotal(items), 0);
});

test('membership total respects eligibility and the payable total', () => {
  const excludedDiscount = { ...discount, counts_toward_membership: false };
  assert.equal(calculateMembershipTotal([charge, excludedDiscount]), 800);
  const excludedCharge = { ...charge, counts_toward_membership: false };
  assert.equal(calculateMembershipTotal([excludedCharge, discount]), 0);
});

test('empty and string inputs retain the editor calculation behavior', () => {
  assert.equal(lineItemTotal({ ...discount, quantity: '2', unit_price: '200' }), -400);
  assert.equal(lineItemTotal({ ...discount, unit_price: '' }), 0);
  assert.equal(lineItemTotal({ ...charge, unit_price: -200 }), 0);
  assert.equal(calculateTotal([]), 0);
});
