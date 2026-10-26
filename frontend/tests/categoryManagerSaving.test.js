import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source = readFileSync(new URL('../src/components/admin/ProductCategoryManager.vue', import.meta.url), 'utf8');
const save = source.match(/async function save\(operation, success\) \{[\s\S]*?\n\}/)[0];

function harness(refresh) {
  const emitted = [];
  const initial = { id: 1, name: '機油', sort_order: 0, is_active: 1 };
  const context = vm.createContext({
    canEdit: { value: true }, busy: { value: false }, loading: { value: false },
    error: { value: '' }, message: { value: '' }, categories: { value: [initial] },
    getProductCategories: refresh,
    emit(event, values) { emitted.push([event, values]); },
  });
  context.setCategories = values => { context.categories.value = [...values]; };
  vm.runInContext(`${save}; globalThis.saveChanges = save;`, context);
  return { context, emitted };
}

test('a committed category create succeeds locally even if refreshing the list fails', async () => {
  const { context, emitted } = harness(async () => { throw new Error('offline'); });
  const created = { id: 2, name: '輪胎', sort_order: 1, is_active: 1 };
  assert.equal(await context.saveChanges(async () => created, '分類已新增。'), true);
  assert.deepEqual(context.categories.value.map(category => category.id), [1, 2]);
  assert.match(context.message.value, /分類已新增/);
  assert.match(context.message.value, /無須再次儲存/);
  assert.equal(context.error.value, '');
  assert.equal(context.busy.value, false);
  assert.equal(emitted.length, 1);
});

test('committed reorder and rename results replace local data before a failed refresh', async () => {
  const { context } = harness(async () => { throw new Error('offline'); });
  const renamed = { id: 1, name: '更名後的機油', sort_order: 0, is_active: 1 };
  await context.saveChanges(async () => renamed, '名稱已儲存。');
  assert.equal(context.categories.value.length, 1);
  assert.equal(context.categories.value[0].name, renamed.name);
  const reordered = [{ id: 2, name: '輪胎', sort_order: 0 }, { ...renamed, sort_order: 1 }];
  await context.saveChanges(async () => reordered, '排序已儲存。');
  assert.deepEqual(context.categories.value.map(category => category.id), [2, 1]);
});

test('failed writes preserve local changes and show the server error', async () => {
  let reads = 0;
  const { context, emitted } = harness(async () => { reads += 1; return []; });
  const before = context.categories.value;
  const result = await context.saveChanges(async () => { throw { response: { data: { detail: '分類清單已變動' } } }; }, '已儲存');
  assert.equal(result, false);
  assert.equal(context.categories.value, before);
  assert.equal(context.error.value, '分類清單已變動');
  assert.equal(context.message.value, '');
  assert.equal(reads, 0);
  assert.equal(emitted.length, 0);
});
