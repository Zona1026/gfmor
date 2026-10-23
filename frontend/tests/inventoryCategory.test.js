import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source = readFileSync(new URL('../src/views/admin/Inventory.vue', import.meta.url), 'utf8');
const save = source.match(/async function submitCreateItem\(\) \{[\s\S]*?\n\}/)[0];

function harness(categoryName, editingId = null) {
  const calls = [];
  const context = vm.createContext({
    FormData, savingCreate: { value: false },
    createForm: { name: 'Tire', category_name: categoryName, price: 100, stock: 1, inventory_type: 'PART', is_active: 1 },
    createItemType: { value: 'PART' }, selectedCreateFile: { value: null }, editingItemId: { value: editingId },
    appendProductDetails() {},
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
    assert.equal(payload.has('category_ids'), false);
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
