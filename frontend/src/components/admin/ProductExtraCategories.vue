<template>
  <fieldset class="extra-categories">
    <legend>分類2（可複選）</legend>
    <div class="choices">
      <label v-for="category in options" :key="category.id">
        <input v-model="form.extra_category_ids" type="checkbox" :value="String(category.id)" />
        {{ category.name }}{{ category.is_active ? '' : '（已停用）' }}
      </label>
      <span v-if="loading">載入中…</span>
      <span v-else-if="!options.length && !error">尚無分類2</span>
    </div>
    <button v-if="canDefine" type="button" @click="showManagement = !showManagement">{{ showManagement ? '收起管理' : '管理分類2' }}</button>
    <p v-if="error" class="error" role="alert">{{ error }} <button type="button" @click="load">重新載入</button></p>
    <div v-if="showManagement && canDefine" class="management">
      <div class="name-row">
        <input v-model.trim="newName" aria-label="新增分類2名稱" maxlength="100" placeholder="例如：活動特價" @keydown.enter.prevent="add" />
        <button type="button" :disabled="busy || !newName" @click="add">新增分類</button>
      </div>
      <div v-for="category in categories" :key="category.id" class="name-row">
        <input v-model.trim="draftNames[category.id]" :aria-label="`分類2 ${category.name} 名稱`" maxlength="100" @keydown.enter.prevent="rename(category)" />
        <button type="button" :disabled="busy || !draftNames[category.id]" @click="rename(category)">儲存名稱</button>
        <button type="button" :disabled="busy" @click="toggle(category)">{{ category.is_active ? '停用' : '啟用' }}</button>
      </div>
    </div>
  </fieldset>
</template>
<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useAuthStore } from '../../store/auth';
import { createProductExtraCategory, getProductExtraCategories, updateProductExtraCategory } from '../../api/admin';
const props = defineProps({ form: { type: Object, required: true } });
const auth = useAuthStore();
const canDefine = computed(() => auth.adminUser?.role === '最高級');
const categories = ref([]);
const options = computed(() => categories.value.filter(category => category.is_active || props.form.extra_category_ids.includes(String(category.id))));
const showManagement = ref(false);
const loading = ref(false);
const busy = ref(false);
const newName = ref('');
const error = ref('');
const draftNames = reactive({});
function setCategories(values) {
  categories.value = values;
  values.forEach(category => { draftNames[category.id] = category.name; });
}
async function load() {
  loading.value = true;
  error.value = '';
  try { setCategories(await getProductExtraCategories()); }
  catch { error.value = '分類2載入失敗。'; }
  finally { loading.value = false; }
}
async function save(operation) {
  if (busy.value) return;
  busy.value = true;
  error.value = '';
  try { await operation(); }
  catch (err) { error.value = typeof err.response?.data?.detail === 'string' ? err.response.data.detail : '分類2儲存失敗，請確認名稱後重試。'; }
  finally { busy.value = false; }
}
function add() {
  if (!newName.value) return;
  return save(async () => {
    const category = await createProductExtraCategory({ name: newName.value });
    setCategories([...categories.value, category]);
    props.form.extra_category_ids = [...new Set([...props.form.extra_category_ids, String(category.id)])];
    newName.value = '';
  });
}
function rename(category) {
  return save(async () => {
    const updated = await updateProductExtraCategory(category.id, { name: draftNames[category.id] });
    setCategories(categories.value.map(entry => entry.id === updated.id ? updated : entry));
  });
}
function toggle(category) {
  return save(async () => {
    const updated = await updateProductExtraCategory(category.id, { is_active: category.is_active ? 0 : 1 });
    setCategories(categories.value.map(entry => entry.id === updated.id ? updated : entry));
  });
}
onMounted(load);
</script>
<style scoped>
.extra-categories { min-width: 0; margin: 0 0 1rem; padding: 0.8rem; border: 1px solid #444; border-radius: 6px; }
.choices { display: flex; flex-wrap: wrap; gap: 0.7rem 1rem; margin-bottom: 0.7rem; }
legend, span { font-size: 0.86rem; }
.choices label { display: flex; flex-direction: row; align-items: center; gap: 0.4rem; font-size: 0.86rem; cursor: pointer; }
.choices input { width: auto; margin: 0; }
button { padding: 0.45rem 0.6rem; background: transparent; color: #ddd; border: 1px solid #555; border-radius: 6px; cursor: pointer; white-space: nowrap; }
button:disabled { opacity: 0.5; }
.management { display: grid; gap: 0.6rem; margin-top: 0.7rem; }
.name-row { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
.name-row input { flex: 1; min-width: 100px; box-sizing: border-box; background: #101118; color: #eee; border: 1px solid #444; border-radius: 6px; padding: 0.55rem; }
.error { color: #ffb74d; font-size: 0.85rem; }
</style>
