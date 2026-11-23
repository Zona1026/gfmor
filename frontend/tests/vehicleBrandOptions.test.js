import assert from 'node:assert/strict';
import test from 'node:test';
import { vehicleBrandOptions } from '../src/utils/vehicleBrandOptions.js';

test('brand dropdown removes blanks and duplicates without changing its source', () => {
  const source = [' SYM ', '', 'YAMAHA', 'SYM', null];
  assert.deepEqual(vehicleBrandOptions(source), ['SYM', 'YAMAHA']);
  assert.deepEqual(source, [' SYM ', '', 'YAMAHA', 'SYM', null]);
});

test('current historical or inactive values remain selectable with empty or refreshed options', () => {
  assert.deepEqual(vehicleBrandOptions([], 'Legacy type'), ['Legacy type']);
  assert.deepEqual(vehicleBrandOptions(['New type'], 'Legacy type'), ['Legacy type', 'New type']);
  assert.deepEqual(vehicleBrandOptions(['SYM'], 'SYM'), ['SYM']);
  assert.deepEqual(vehicleBrandOptions([], ''), []);
});
