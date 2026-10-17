import assert from 'node:assert/strict';
import test from 'node:test';
import { manufacturerOptions, filterWorkOrderProducts, supplierOptions, filterPickerProducts } from '../src/utils/workOrderProductPicker.js';

const products = [
  { id: 1, manufacturer: 'SYM', categories: [{ id: 10, name: '機油' }], supplier_wholesale_prices: [{ supplier_name: '進貨商甲' }] },
  { id: 2, manufacturer: ' SYM ', categories: [{ id: 10, name: '機油' }], supplier_wholesale_prices: [{ supplier_name: '進貨商乙' }] },
  { id: 3, manufacturer: 'YAMAHA', categories: [{ id: 20, name: '煞車' }], supplier_wholesale_prices: [{ supplier_name: '進貨商甲' }] },
  { id: 4, manufacturer: null, categories: [{ id: 10, name: '機油' }], supplier_wholesale_prices: [{ supplier_name: '進貨商甲' }] },
];

test('工單廠商選項使用庫存廠商、去除空白重複並隨分類篩選', () => {
  assert.deepEqual(manufacturerOptions(products), ['SYM', 'YAMAHA']);
  assert.deepEqual(manufacturerOptions(products, '10'), ['SYM']);
  assert.deepEqual(manufacturerOptions(products, '20'), ['YAMAHA']);
});

test('工單依庫存廠商篩選，不受進貨商相同或不同影響', () => {
  assert.deepEqual(filterWorkOrderProducts(products, '', 'SYM').map(p => p.id), [1, 2]);
  assert.deepEqual(filterWorkOrderProducts(products, '20', 'SYM'), []);
  assert.deepEqual(filterWorkOrderProducts(products, '', '進貨商甲'), []);
  assert.deepEqual(filterWorkOrderProducts(products).map(p => p.id), [1, 2, 3, 4]);
});

test('優惠活動的進貨廠商選項及篩選維持原有來源', () => {
  assert.deepEqual(supplierOptions(products), ['進貨商乙', '進貨商甲'].sort((a,b) => a.localeCompare(b,'zh-TW')));
  assert.deepEqual(filterPickerProducts(products, '', '進貨商甲').map(p => p.id), [1, 3, 4]);
});
