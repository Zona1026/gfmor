import assert from 'node:assert/strict';
import test from 'node:test';
import { categoryOptions, productCategories, manufacturerOptions, filterWorkOrderProducts, supplierOptions, filterPickerProducts } from '../src/utils/workOrderProductPicker.js';

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

test('分類依共用排序排列，多分類商品不產生重複選項', () => {
  const first = { id: 20, name: '輪胎', sort_order: 0, is_active: 1 };
  const last = { id: 10, name: '機油', sort_order: 9, is_active: 1 };
  const catalog = [{ categories: [last, first] }, { categories: [first] }];
  assert.deepEqual(categoryOptions(catalog).map(category => category.value), ['20', '10']);
  assert.equal(productCategories(catalog[0])[0].sort_order, 9);
  assert.deepEqual(categoryOptions([{ category_id: 20, category_info: first }, { category_id: 10, category_info: last }]).map(category => category.value), ['20', '10']);
});

test('停用分類不提供新選擇，但保留原選取及庫存篩選', () => {
  const catalog = [{ categories: [{ id: 1, name: '機油', sort_order: 0, is_active: 0 }, { id: 2, name: '輪胎', sort_order: 1, is_active: 1 }] }];
  assert.deepEqual(categoryOptions(catalog).map(category => category.value), ['2']);
  assert.deepEqual(categoryOptions(catalog, { selectedValue: '1' }).map(category => category.value), ['1', '2']);
  assert.deepEqual(categoryOptions(catalog, { includeInactive: true }).map(category => category.value), ['1', '2']);
  assert.equal(filterPickerProducts(catalog, '1').length, 1);
});

test('同排序同名時以 ID 穩定排列，舊文字分類仍可篩選', () => {
  const catalog = [{ categories: [{ id: 5, name: '同名', sort_order: 2 }, { id: 3, name: '同名', sort_order: 2 }] }, { category: '舊分類' }];
  assert.deepEqual(categoryOptions(catalog).filter(category => category.name === '同名').map(category => category.value), ['3', '5']);
  assert.equal(filterPickerProducts(catalog, 'name:舊分類').length, 1);
});
