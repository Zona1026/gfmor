<template>
  <div class="admin-management">
    <div class="section-header">
      <h2>系統與權限</h2>
      <button 
        class="btn btn-primary" 
        @click="showCreateModal = true"
        :disabled="adminUser?.role !== '最高級'"
        :title="adminUser?.role !== '最高級' ? '僅最高級管理員可新增管理員' : ''"
      >
        ＋ 新增管理員
      </button>
    </div>

    <div v-if="adminUser?.role !== '最高級'" class="permission-alert">
      🔒 您的登入角色為「{{ adminUser?.role || '一般' }}」，僅限檢視列表。如需新增、修改或刪除，請聯絡最高級系統管理員。
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else class="admin-table-wrap">
      <table class="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>管理員姓名</th>
            <th>管理員帳號</th>
            <th>權限等級</th>
            <th>建立時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="admin in admins" :key="admin.id">
            <td>#{{ admin.id }}</td>
            <td class="username">{{ admin.full_name || '未設定' }}</td>
            <td class="username">{{ admin.username }}</td>
            <td>
              <span class="role-tag" :class="getRoleClass(admin.role)">
                {{ admin.role || '一般' }}
              </span>
            </td>
            <td class="time">{{ formatDate(admin.created_at) }}</td>
            <td class="actions">
              <button 
                class="btn-edit" 
                @click="openEditModal(admin)"
                :disabled="adminUser?.role !== '最高級'"
                :title="adminUser?.role !== '最高級' ? '僅最高級管理員可編輯' : ''"
              >
                編輯
              </button>
              <button
                class="btn-delete"
                @click="deleteAdminHandler(admin)"
                :disabled="(admins?.length || 0) <= 1 || adminUser?.role !== '最高級'"
                :title="adminUser?.role !== '最高級' ? '僅最高級管理員可刪除' : ''"
              >
                刪除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="(admins?.length || 0) <= 1" class="hint">⚠️ 系統必須保留至少一個管理員帳號。</p>
    </div>

    <!-- 新增管理員 Modal -->
    <div class="modal-overlay" v-if="showCreateModal" @click.self="showCreateModal = false">
      <div class="modal">
        <h3>新增管理員帳號</h3>
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>管理員姓名</label>
            <input type="text" v-model="createForm.full_name" placeholder="例如：小王" />
          </div>
          <div class="form-group">
            <label>管理員帳號</label>
            <input type="text" v-model="createForm.username" required placeholder="例如：staff_01" />
          </div>
          <div class="form-group">
            <label>權限等級</label>
            <select v-model="createForm.role" class="form-select" required>
              <option value="一般">一般 (一般帳號)</option>
              <option value="管理層">管理層 (主管職等)</option>
              <option value="最高級">最高級 (超級管理員)</option>
            </select>
          </div>
          <div class="form-group">
            <label>密碼</label>
            <input type="password" v-model="createForm.password" required placeholder="請輸入密碼" />
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="showCreateModal = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
              {{ isSubmitting ? '建立中...' : '確認建立' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 編輯管理員 Modal -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="showEditModal = false">
      <div class="modal">
        <h3>編輯管理員</h3>
        <form @submit.prevent="handleUpdate">
          <div class="form-group">
            <label>管理員姓名</label>
            <input v-model="editForm.full_name" />
          </div>
          <div class="form-group">
            <label>管理員帳號</label>
            <input v-model="editForm.username" required />
          </div>
          <div class="form-group">
            <label>權限等級</label>
            <select v-model="editForm.role" class="form-select" required>
              <option value="一般">一般 (一般帳號)</option>
              <option value="管理層">管理層 (主管職等)</option>
              <option value="最高級">最高級 (超級管理員)</option>
            </select>
          </div>
          <div class="form-group">
            <label>變更密碼 (不變更則留空)</label>
            <input v-model="editForm.password" type="password" />
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="showEditModal = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
              {{ isSubmitting ? '儲存中...' : '儲存修改' }}
            </button>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useAuthStore } from '../../store/auth';
import { getAdmins, createAdmin, deleteAdmin, updateAdmin } from '../../api/admin';

const authStore = useAuthStore();
const { adminUser } = storeToRefs(authStore);

const admins = ref([]);
const loading = ref(false);
const isSubmitting = ref(false); // Renamed from 'submitting' for consistency
const showCreateModal = ref(false);
const showEditModal = ref(false);

const createForm = ref({
  username: '',
  password: '',
  full_name: '',
  role: '一般'
});

const editForm = ref({
  id: null,
  username: '',
  full_name: '',
  password: '',
  role: '一般'
});

const fetchAdmins = async () => {
  loading.value = true;
  try {
    admins.value = await getAdmins();
  } catch (e) {
    console.error(e);
    alert('無法取得管理員列表');
  } finally {
    loading.value = false;
  }
};

const handleCreate = async () => {
  isSubmitting.value = true;
  try {
    await createAdmin(createForm.value);
    alert('管理員帳號已建立');
    showCreateModal.value = false;
    createForm.value = { username: '', password: '', full_name: '', role: '一般' };
    fetchAdmins();
  } catch (e) {
    console.error(e);
    alert('建立失敗：' + (e.response?.data?.detail || '服務錯誤'));
  } finally {
    isSubmitting.value = false;
  }
};

const openEditModal = (admin) => {
  editForm.value = {
    id: admin.id,
    username: admin.username,
    full_name: admin.full_name || '',
    password: '',
    role: admin.role || '一般'
  };
  showEditModal.value = true;
};

const handleUpdate = async () => {
  isSubmitting.value = true;
  try {
    const { id, ...data } = editForm.value;
    if (!data.password) delete data.password; // Don't send empty password if not changed
    await updateAdmin(id, data);
    alert('管理員更新成功');
    showEditModal.value = false;
    fetchAdmins();
  } catch (e) {
    console.error(e);
    alert('更新失敗：' + (e.response?.data?.detail || '服務錯誤'));
  } finally {
    isSubmitting.value = false;
  }
};

const deleteAdminHandler = async (admin) => { // Renamed from handleDelete
  if (!confirm(`確定要刪除管理員 [${admin.username}] 嗎？此動作無法復原。`)) return;

  try {
    await deleteAdmin(admin.id);
    alert('已刪除');
    fetchAdmins();
  } catch (e) {
    console.error(e);
    alert('刪除失敗：' + (e.response?.data?.detail || '服務錯誤'));
  }
};

const getRoleClass = (role) => {
  if (role === '最高級') return 'role-super';
  if (role === '管理層') return 'role-manager';
  return 'role-staff';
};

const formatDate = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

onMounted(fetchAdmins);
</script>

<style lang="scss" scoped>
@use '../../assets/_variables.scss' as *;

.admin-management {
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
    h2 { margin: 0; color: $primary-light; }
  }

  .loading { text-align: center; padding: 3rem; color: $text-disabled; }

  .admin-table-wrap {
    background: $background-color;
    border: 1px solid $medium-grey;
    border-radius: 8px;
    overflow: hidden;

    .admin-table {
      width: 100%;
      border-collapse: collapse;

      th, td {
        padding: 1rem;
        text-align: left;
        border-bottom: 1px solid rgba($medium-grey, 0.5);
      }

      th {
        background: rgba($medium-grey, 0.2);
        color: $text-disabled;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
      }

      .username { font-weight: bold; color: $primary-light; }
      .time { color: $text-disabled; font-size: 0.85rem; }

      .actions {
        display: flex;
        gap: 0.5rem;
      }
      .btn-edit {
        background-color: $primary-color;
        color: $background-color;
        border: none;
        padding: 0.3rem 0.6rem;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.85rem;
        &:hover { background-color: $primary-dark; }
      }
      .btn-delete {
        background-color: #ff4d4f;
        color: white;
        border: none;
        padding: 0.3rem 0.6rem;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.85rem;
        &:hover { background-color: #ff7875; }
        &:disabled { opacity: 0.3; cursor: not-allowed; }
      }
    }

    .hint {
      padding: 1rem;
      margin: 0;
      font-size: 0.85rem;
      color: $text-disabled;
      background: rgba($medium-grey, 0.1);
    }
  }

  .btn {
    padding: 0.5rem 1rem;
    border-radius: $border-radius;
    font-weight: bold;
    cursor: pointer;
    border: none;
    transition: 0.2s;

    &.btn-primary { background: $primary-color; color: #fff; &:hover { background: $primary-dark; } }
    &.btn-outline { background: transparent; border: 1px solid $medium-grey; color: $text-secondary; &:hover { background: $medium-grey; } }
    &.btn-sm { padding: 0.25rem 0.6rem; font-size: 0.8rem; }
  }

  /* Modal */
  .modal-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000;
  }
  .modal {
    background: $dark-grey; border: 1px solid $medium-grey; border-radius: 12px;
    padding: 2rem; width: 400px; max-width: 90%;
    h3 { margin-top: 0; color: $primary-light; margin-bottom: 1.5rem; }
    .form-group {
      margin-bottom: 1.2rem;
      label { display: block; margin-bottom: 0.5rem; color: $text-secondary; font-size: 0.9rem; }
      input, .form-select {
        width: 100%; padding: 0.8rem; background: $background-color; border: 1px solid $medium-grey;
        border-radius: $border-radius; color: $text-primary;
        &:focus { border-color: $primary-color; outline: none; }
      }
      .form-select {
        cursor: pointer;
        option { background: $dark-grey; color: $text-primary; }
      }
    }
    .form-actions { display: flex; justify-content: flex-end; gap: 0.8rem; margin-top: 2rem; }
  }

  /* Roles & Permission styles */
  .permission-alert {
    background: rgba(#ff4d4f, 0.08);
    border: 1px dashed rgba(#ff4d4f, 0.3);
    color: #ff7875;
    padding: 0.8rem 1.2rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    font-size: 0.9rem;
  }

  .role-tag {
    padding: 0.25rem 0.6rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: bold;
    display: inline-block;
    text-align: center;

    &.role-super {
      background: linear-gradient(135deg, rgba(#ff4d4f, 0.25) 0%, rgba(#fa8c16, 0.25) 100%);
      color: #ffa940;
      border: 1px solid rgba(#fa8c16, 0.45);
    }
    &.role-manager {
      background: linear-gradient(135deg, rgba(#722ed1, 0.25) 0%, rgba(#13c2c2, 0.25) 100%);
      color: #d3adf7;
      border: 1px solid rgba(#d3adf7, 0.45);
    }
    &.role-staff {
      background: linear-gradient(135deg, rgba(#1890ff, 0.2) 0%, rgba(#52c41a, 0.2) 100%);
      color: #40a9ff;
      border: 1px solid rgba(#40a9ff, 0.4);
    }
  }

  .btn:disabled, .btn-edit:disabled, .btn-delete:disabled {
    opacity: 0.4 !important;
    cursor: not-allowed !important;
    background-color: #434343 !important;
    color: #a6a6a6 !important;
    border-color: #303030 !important;
  }
}
</style>
