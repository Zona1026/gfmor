import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import { appendProductDetails, productDetailsForm } from '../src/utils/productDetails.js';
import { compareCategories } from '../src/utils/workOrderProductPicker.js';

const source = readFileSync(new URL('../src/views/admin/Inventory.vue', import.meta.url), 'utf8');
const save = source.match(/async function submitCreateItem\(\) \{[\s\S]*?\n\}/)[0];

function harness(categoryName, editingId = null) {
  const calls = [];
  const context = vm.createContext({
    FormData, savingCreate: { value: false }, savingCategory: { value: false },
    createForm: { ...productDetailsForm(), name: 'Tire', category_name: categoryName, price: 100, stock: 1, inventory_type: 'PART', is_active: 1 },
    createItemType: { value: 'PART' }, selectedCreateFile: { value: null }, editingItemId: { value: editingId },
    appendProductDetails,
    async createProduct(data) { calls.push(['create', data]); },
    async updateProduct(id, data) { calls.push(['update', id, data]); },
    closeCreateModal() { calls.push(['close']); },
    async fetchItems() { calls.push(['items']); },
    async fetchCategories() { calls.push(['categories']); },
    alert(message) { throw new Error(message); },
  });
  vm.runInContext(`${save}; globalThis.saveItem = submitCreateItem;`, context);
  return { context, calls };
}

for (const editingId of [null, 42]) {
  test(`saving ${editingId ? 'an existing' : 'a new'} part submits a typed category and refreshes suggestions`, async () => {
    const { context, calls } = harness('  新零件分類  ', editingId);
    await context.saveItem();
    const payload = calls[0].at(-1);
    assert.equal(calls[0][0], editingId ? 'update' : 'create');
    assert.equal(payload.get('category'), '新零件分類');
    assert.equal(payload.has('category_id'), false);
    assert.equal(payload.get('category_ids'), '[]');
    assert.ok(calls.some(call => call[0] === 'categories'));
    assert.equal(context.savingCreate.value, false);
  });
}

test('clearing a category explicitly clears the category links on the server', async () => {
  const { context, calls } = harness(' ', 42);
  await context.saveItem();
  const payload = calls[0].at(-1);
  assert.equal(payload.get('category_ids'), '[]');
  assert.equal(payload.has('category'), false);
});

test('selecting a primary keeps additional categories in the shared payload', async () => {
  const { context, calls } = harness('New primary', 42);
  context.createForm.category_ids = ['7', '9'];
  await context.saveItem();
  const payload = calls[0].at(-1);
  assert.equal(payload.get('category'), 'New primary');
  assert.equal(payload.get('category_ids'), '[7,9]');
});

const createCategory = source.match(/async function submitCreateCategory\(\) \{[\s\S]*?\n\}/)[0];
function categoryHarness(overrides = {}) {
  const calls = [];
  const context = vm.createContext({
    canUseCriticalInventory: { value: true }, savingCategory: { value: false }, savingCreate: { value: false },
    newCategoryName: { value: '  新耗材  ' }, categories: { value: [] },
    categoryMessage: { value: '' }, categoryError: { value: '' },
    itemModalSession: 1, showCreateModal: { value: true }, showCategoryForm: { value: true },
    createForm: { category_name: '原分類' }, compareCategories,
    async createProductCategory(data) { calls.push(data); return { id: 8, name: data.name, sort_order: 3, is_active: 1 }; },
    async fetchCategories() {},
    ...overrides,
  });
  vm.runInContext(`${createCategory}; globalThis.addCategory = submitCreateCategory;`, context);
  return { context, calls };
}

test('a successful category create remains selected when refreshing the list fails', async () => {
  const { context, calls } = categoryHarness({ async fetchCategories() { throw new Error('offline'); } });
  await context.addCategory();
  assert.equal(calls.length, 1);
  assert.equal(context.createForm.category_name, '新耗材');
  assert.equal(context.categories.value[0].name, '新耗材');
  assert.match(context.categoryMessage.value, /已建立並選取/);
  assert.match(context.categoryMessage.value, /無須再次新增/);
  assert.equal(context.categoryError.value, '');
  assert.equal(context.showCategoryForm.value, false);
  assert.equal(context.savingCategory.value, false);
});

test('retrying an existing category reuses it instead of sending another create', async () => {
  const { context, calls } = categoryHarness();
  await context.addCategory();
  context.newCategoryName.value = '新耗材';
  await context.addCategory();
  assert.equal(calls.length, 1);
  assert.equal(context.createForm.category_name, '新耗材');
  assert.match(context.categoryMessage.value, /既有分類/);
});

test('double submission cannot create twice while the first request is pending', async () => {
  let complete;
  let count = 0;
  const { context } = categoryHarness({ createProductCategory() {
    count += 1;
    return new Promise(resolve => { complete = resolve; });
  } });
  const pending = context.addCategory();
  await context.addCategory();
  assert.equal(count, 1);
  complete({ id: 8, name: '新耗材', sort_order: 3, is_active: 1 });
  await pending;
  assert.equal(context.createForm.category_name, '新耗材');
});

test('a late create response cannot overwrite a closed or newly opened item form', async () => {
  for (const reopen of [false, true]) {
    let complete;
    const { context } = categoryHarness({ createProductCategory: () => new Promise(resolve => { complete = resolve; }) });
    const pending = context.addCategory();
    context.itemModalSession += 1;
    context.showCreateModal.value = reopen;
    context.createForm.category_name = '另一張表單的分類';
    complete({ id: 8, name: '新耗材', sort_order: 3, is_active: 1 });
    await pending;
    assert.equal(context.createForm.category_name, '另一張表單的分類');
    assert.equal(context.categoryMessage.value, '');
    assert.equal(context.categories.value[0].name, '新耗材');
  }
});

test('inactive categories and non-super roles cannot create or select categories through the add action', async () => {
  const inactive = categoryHarness({ categories: { value: [{ id: 8, name: '新耗材', is_active: 0 }] } });
  await inactive.context.addCategory();
  assert.equal(inactive.calls.length, 0);
  assert.equal(inactive.context.createForm.category_name, '原分類');
  assert.match(inactive.context.categoryError.value, /已停用/);
  const manager = categoryHarness({ canUseCriticalInventory: { value: false } });
  await manager.context.addCategory();
  assert.equal(manager.calls.length, 0);
});

test('a failed create retains the original selection and the entered name for correction', async () => {
  const { context } = categoryHarness({ async createProductCategory() { throw { response: { data: { detail: '分類名稱已存在' } } }; } });
  await context.addCategory();
  assert.equal(context.createForm.category_name, '原分類');
  assert.equal(context.newCategoryName.value, '  新耗材  ');
  assert.match(context.categoryError.value, /分類名稱已存在/);
  assert.equal(context.showCategoryForm.value, true);
});

test('item save waits for category creation to finish', async () => {
  const { context, calls } = harness('機油');
  context.savingCategory.value = true;
  await context.saveItem();
  assert.equal(calls.length, 0);
});
