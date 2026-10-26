<template>
  <section class="category-manager" aria-labelledby="category-manager-title" :aria-busy="busy || loading">
    <div class="heading">
      <div>
        <h3 id="category-manager-title">分類列表及排序</h3>
        <p>工單、庫存與商城共用此順序。拖曳或使用上下按鈕調整後，請儲存排序。</p>
      </div>
      <button type="button" :disabled="busy || loading" @click="reload">重新載入</button>
    </div>
    <p v-if="!canEdit">僅最高級管理員可修改分類。</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="message" role="status">{{ message }}</p>
    <p v-if="dirty" class="notice" role="status">排序尚未儲存。請先儲存或取消排序，再新增、改名或啟停分類。</p>
    <div v-if="canEdit" class="actions">
      <button type="button" :disabled="!dirty || busy || loading" @click="saveOrder">儲存排序</button>
      <button type="button" :disabled="!dirty || busy || loading" @click="cancelOrder">取消排序</button>
    </div>
    <form v-if="canEdit" class="new-category" @submit.prevent="addCategory">
      <label>新分類名稱<input v-model.trim="newName" maxlength="50" :disabled="busy || loading || dirty" required /></label>
      <button type="submit" :disabled="busy || loading || dirty || !newName">新增分類</button>
    </form>
    <p v-if="loading">載入中…</p>
    <ol v-else class="category-list" aria-label="分類順序">
      <li v-for="(category, index) in categories" :key="category.id" :class="{ dragging: draggingId === category.id }"
          @dragover.prevent @drop.prevent="dropCategory(category.id)">
        <div class="category-info">
          <span class="position">{{ index + 1 }}</span>
          <template v-if="editingId === category.id">
            <label>分類名稱<input v-model.trim="editName" maxlength="50" :disabled="busy" @keydown.enter.prevent="renameCategory(category)" /></label>
          </template>
          <strong v-else>{{ category.name }}</strong>
          <span class="status" :class="{ inactive: !category.is_active }">{{ category.is_active ? '啟用' : '停用' }}</span>
        </div>
        <div v-if="canEdit" class="row-actions">
          <template v-if="editingId === category.id">
            <button type="button" :disabled="busy || !editName" @click="renameCategory(category)">儲存名稱</button>
            <button type="button" :disabled="busy" @click="editingId = null">取消改名</button>
          </template>
          <template v-else>
            <button class="drag-handle" type="button" :draggable="canReorder" :disabled="!canReorder"
                    :aria-label="`拖曳 ${category.name}`" @dragstart="startDrag($event, category.id)" @dragend="draggingId = null">⠿ 拖曳</button>
            <button type="button" :disabled="!canReorder || index === 0" :aria-label="`上移 ${category.name}`" @click="moveCategory(index, index - 1)">↑ 上移</button>
            <button type="button" :disabled="!canReorder || index === categories.length - 1" :aria-label="`下移 ${category.name}`" @click="moveCategory(index, index + 1)">↓ 下移</button>
            <button type="button" :disabled="busy || dirty || editingId !== null" @click="startRename(category)">改名</button>
            <button type="button" :disabled="busy || dirty || editingId !== null" @click="toggleCategory(category)">{{ category.is_active ? '停用' : '啟用' }}</button>
          </template>
        </div>
      </li>
    </ol>
    <p v-if="!loading && !categories.length && !error">尚無分類。</p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import Swal from 'sweetalert2';
import { useAuthStore } from '../../store/auth';
import { createProductCategory, getProductCategories, reorderProductCategories, toggleProductCategory, updateProductCategory } from '../../api/admin';
import { compareCategories } from '../../utils/workOrderProductPicker';

const emit = defineEmits(['changed']);
const auth = useAuthStore();
const canEdit = computed(() => auth.adminUser?.role === '最高級');
const categories = ref([]);
const original = ref([]);
const loading = ref(false);
const busy = ref(false);
const error = ref('');
const message = ref('');
const newName = ref('');
const editingId = ref(null);
const editName = ref('');
const draggingId = ref(null);
const dirty = computed(() => categories.value.some((category, index) => category.id !== original.value[index]?.id));
const canReorder = computed(() => canEdit.value && !loading.value && !busy.value && editingId.value === null);

function setCategories(values) {
  categories.value = [...values].sort(compareCategories);
  original.value = categories.value.map(category => ({ ...category }));
  editingId.value = null;
}
async function load() {
  loading.value = true;
  error.value = '';
  try { setCategories(await getProductCategories()); }
  catch { error.value = '分類載入失敗，請重新載入。'; }
  finally { loading.value = false; }
}
async function confirmLeave() {
  if (busy.value) return false;
  if (!dirty.value) return true;
  const result = await Swal.fire({
    title: '分類排序尚未儲存',
    text: '離開將放棄這次排序修改。',
    showCancelButton: true,
    confirmButtonText: '放棄修改並離開',
    cancelButtonText: '繼續編輯',
    focusCancel: true,
    background: '#222',
    color: '#eee',
  });
  return result.isConfirmed;
}
defineExpose({ confirmLeave });
onBeforeRouteLeave(confirmLeave);
function beforeUnload(event) {
  if (dirty.value || busy.value) { event.preventDefault(); event.returnValue = ''; }
}
onMounted(() => { window.addEventListener('beforeunload', beforeUnload); load(); });
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload));
async function reload() {
  if (!await confirmLeave()) return;
  message.value = '';
  await load();
}
function cancelOrder() {
  categories.value = original.value.map(category => ({ ...category }));
  error.value = '';
  message.value = '';
}
function moveCategory(from, to) {
  if (!canReorder.value || from < 0 || to < 0 || from >= categories.value.length || to >= categories.value.length) return;
  const [category] = categories.value.splice(from, 1);
  categories.value.splice(to, 0, category);
  message.value = '';
}
function startDrag(event, id) {
  if (!canReorder.value) { event.preventDefault(); return; }
  draggingId.value = id;
  event.dataTransfer.effectAllowed = 'move';
  event.dataTransfer.setData('text/plain', String(id));
}
function dropCategory(id) {
  if (draggingId.value === null) return;
  moveCategory(categories.value.findIndex(category => category.id === draggingId.value), categories.value.findIndex(category => category.id === id));
  draggingId.value = null;
}
async function save(operation, success) {
  if (!canEdit.value || busy.value || loading.value) return;
  busy.value = true;
  error.value = '';
  message.value = '';
  try {
    const saved = await operation();
    // Keep a successful write even if reading back the list fails.
    setCategories(Array.isArray(saved) ? saved : [...categories.value.filter(category => category.id !== saved.id), saved]);
    emit('changed', categories.value);
    message.value = success;
    try {
      setCategories(await getProductCategories());
      emit('changed', categories.value);
    } catch {
      message.value += ' 清單暫時無法更新，請稍後重新載入；無須再次儲存。';
    }
    return true;
  } catch (failure) {
    error.value = typeof failure.response?.data?.detail === 'string' ? failure.response.data.detail : '儲存失敗，請重新載入確認結果後再試。';
    return false;
  } finally { busy.value = false; }
}
function saveOrder() {
  if (!dirty.value) return;
  return save(() => reorderProductCategories(categories.value.map(category => category.id)), '分類排序已儲存。');
}
async function addCategory() {
  if (dirty.value || !newName.value) return;
  if (await save(() => createProductCategory({ name: newName.value }), '分類已新增。')) newName.value = '';
}
function startRename(category) {
  editingId.value = category.id;
  editName.value = category.name;
}
function renameCategory(category) {
  if (dirty.value || !editName.value) return;
  return save(() => updateProductCategory(category.id, { name: editName.value }), '分類名稱已儲存。');
}
function toggleCategory(category) {
  if (dirty.value) return;
  return save(() => toggleProductCategory(category.id), category.is_active ? '分類已停用，原有商品關聯仍保留。' : '分類已啟用。');
}
</script>

<style scoped>
.category-manager { color: #eee; background: #222; border: 1px solid #444; border-radius: 8px; padding: 1rem; }
.heading, .category-info, .row-actions, .actions, .new-category { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }
.heading { justify-content: space-between; }
h3 { margin: 0; }
p { color: #bbb; line-height: 1.6; }
button, input { border: 1px solid #555; border-radius: 5px; padding: .55rem .7rem; background: #161616; color: #eee; font: inherit; }
button { cursor: pointer; min-height: 40px; }
button:disabled { opacity: .45; cursor: not-allowed; }
button:focus-visible, input:focus-visible { outline: 2px solid #ff6868; outline-offset: 2px; }
label { display: flex; align-items: center; flex-wrap: wrap; gap: .5rem; }
.new-category { margin: 1rem 0; }
.category-list { padding: 0; list-style: none; }
li { display: flex; align-items: center; justify-content: space-between; gap: .8rem; padding: .85rem 0; border-bottom: 1px solid #444; }
.category-info { min-width: 0; overflow-wrap: anywhere; }
.position { color: #aaa; min-width: 1.5rem; }
.status { font-size: .8rem; color: #a9dfb4; }
.inactive { color: #aaa; }
.notice { color: #ffd08a; }
.error { color: #ff9292; }
.drag-handle { cursor: grab; }
.dragging { opacity: .45; }
@media (max-width: 700px) { li { align-items: flex-start; flex-direction: column; } .new-category label, input { width: 100%; box-sizing: border-box; } .row-actions { width: 100%; } }
</style>
