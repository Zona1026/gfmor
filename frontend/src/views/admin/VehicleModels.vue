<template>
  <div class="vehicle-models">
    <h2>車種管理</h2>
    <p>工單與商品共用車種選單。自由填寫的工單車種不會自動加入。</p>
    <form class="toolbar" @submit.prevent="add">
      <input v-model.trim="newName" aria-label="新車種名稱" placeholder="輸入新車種" maxlength="200" required />
      <button class="btn btn-primary" :disabled="busy || !newName">新增車種</button>
      <button class="btn btn-outline" type="button" :disabled="busy" @click="load">重新整理</button>
    </form>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="loading" role="status">載入中…</p>
    <div v-else class="table-scroll">
      <table><thead><tr><th>車種名稱</th><th>狀態</th><th v-if="canManage">操作</th></tr></thead>
        <tbody><tr v-for="row in rows" :key="row.id">
          <td><input v-if="canManage" v-model.trim="row.draftName" :aria-label="`車種名稱 ${row.name}`" maxlength="200" /><span v-else>{{ row.name }}</span></td>
          <td>{{ row.is_active ? '啟用' : '停用' }}</td>
          <td v-if="canManage">
            <div class="actions">
            <button class="btn btn-outline" :disabled="busy || !row.draftName || row.draftName === row.name" @click="save(row, { name: row.draftName })">儲存名稱</button>
            <button class="btn btn-outline" :disabled="busy" @click="save(row, { is_active: !row.is_active })">{{ row.is_active ? '停用' : '啟用' }}</button>
            </div>
          </td>
        </tr></tbody>
      </table>
      <p v-if="!rows.length">尚無車種，請新增。</p>
    </div>
    <p v-if="canManage">改名與停用只影響共用選單，既有工單與商品保留原文字。</p>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue';
import { useAuthStore } from '../../store/auth';
import { createProductVehicleModel, getVehicleModelManagement, updateVehicleModel } from '../../api/admin';
const auth = useAuthStore();
const canManage = computed(() => ['管理層', '最高級'].includes(auth.adminUser?.role));
const rows = ref([]), newName = ref(''), busy = ref(false), loading = ref(false), error = ref('');
async function load() {
  loading.value = true;
  error.value = '';
  try { rows.value = (await getVehicleModelManagement()).map(row => ({ ...row, draftName: row.name })); }
  catch (e) { error.value = e.response?.data?.detail || '載入車種失敗，請重新整理。'; }
  finally { loading.value = false; }
}
async function add() {
  busy.value = true; error.value = '';
  try { await createProductVehicleModel(newName.value); newName.value = ''; await load(); }
  catch (e) { error.value = e.response?.data?.detail || '新增車種失敗。'; }
  finally { busy.value = false; }
}
async function save(row, changes) {
  busy.value = true; error.value = '';
  try { const saved = await updateVehicleModel(row.id, changes); Object.assign(row, saved, { draftName: saved.name }); }
  catch (e) { error.value = e.response?.data?.detail || '儲存車種失敗。'; }
  finally { busy.value = false; }
}
onMounted(load);
</script>
<style scoped>
.vehicle-models { display: grid; gap: 1rem; }
h2, p { margin: 0; }
.toolbar, .actions { display: flex; align-items: center; flex-wrap: wrap; gap: .5rem; }
.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; vertical-align: middle; padding: .75rem; border-bottom: 1px solid #ddd; }
input { max-width: 100%; box-sizing: border-box; padding: .65rem; border: 1px solid #424242; border-radius: 8px; background: #212121; color: #eee; font: inherit; }
[role=alert] { color: #ffb4ab; }
</style>
