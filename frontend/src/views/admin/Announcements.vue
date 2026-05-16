<template>
  <div class="admin-announcements">
    <div class="section-header">
      <h2>公告管理</h2>
      <button class="btn btn-primary" @click="openCreateModal">＋ 新增公告</button>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else class="ann-grid">
      <div v-for="ann in announcements" :key="ann.id" class="ann-card" :class="{ inactive: !ann.is_active }">
        <img :src="ann.image_url" :alt="ann.title" class="ann-image" />
        <div class="ann-body">
          <h3>{{ ann.title }}</h3>
          <p v-if="ann.description">{{ ann.description }}</p>
          <small class="meta">排序：{{ ann.sort_order }} ｜ {{ ann.is_active ? '啟用中' : '已停用' }}</small>
        </div>
        <div class="ann-actions">
          <button class="btn btn-sm" @click="openEditModal(ann)">編輯</button>
          <button class="btn btn-sm btn-danger" @click="handleDelete(ann.id)">刪除</button>
        </div>
      </div>
      <div v-if="announcements.length === 0" class="empty">尚無公告，點擊上方按鈕新增第一則公告吧！</div>
    </div>

    <!-- 新增 / 編輯 Modal -->
    <div class="modal-overlay" v-if="showModal" @click.self="showModal = false">
      <div class="modal">
        <h3>{{ isEditing ? '編輯公告' : '新增公告' }}</h3>
        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label>公告標題</label>
            <input type="text" v-model="form.title" required placeholder="例如：春季優惠活動" />
          </div>
          <div class="form-group">
            <label>公告說明 (選填)</label>
            <textarea v-model="form.description" rows="3" placeholder="簡述活動內容..."></textarea>
          </div>
          <div class="form-group">
            <label>排序權重 (數字越小越前面)</label>
            <input type="number" v-model.number="form.sort_order" />
          </div>
          <div class="form-group">
            <label>{{ isEditing ? '更換圖片 (不換則留空)' : '上傳公告圖片' }}</label>
            <input type="file" accept="image/*" @change="onFileChange" ref="fileInput" />
            <small class="tip">📐 建議尺寸：1920 × 1080 px (16:9)，解析度 72dpi，格式 JPG/PNG</small>
          </div>
          <div v-if="previewUrl" class="preview">
            <img :src="previewUrl" alt="Preview" />
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="showModal = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              {{ submitting ? '處理中...' : (isEditing ? '更新' : '上傳') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { getAnnouncements, createAnnouncement, updateAnnouncement, deleteAnnouncement } from '../../api/admin';

const announcements = ref([]);
const loading = ref(false);
const showModal = ref(false);
const isEditing = ref(false);
const editingId = ref(null);
const submitting = ref(false);
const previewUrl = ref('');
const selectedFile = ref(null);
const fileInput = ref(null);

const form = ref({
  title: '',
  description: '',
  sort_order: 0
});

const fetchAnnouncements = async () => {
  loading.value = true;
  try {
    announcements.value = await getAnnouncements();
  } catch (e) {
    console.error('載入公告失敗', e);
  } finally {
    loading.value = false;
  }
};

const openCreateModal = () => {
  isEditing.value = false;
  editingId.value = null;
  form.value = { title: '', description: '', sort_order: 0 };
  previewUrl.value = '';
  selectedFile.value = null;
  showModal.value = true;
};

const openEditModal = (ann) => {
  isEditing.value = true;
  editingId.value = ann.id;
  form.value = {
    title: ann.title,
    description: ann.description || '',
    sort_order: ann.sort_order
  };
  previewUrl.value = ann.image_url;
  selectedFile.value = null;
  showModal.value = true;
};

const onFileChange = (e) => {
  const file = e.target.files[0];
  if (file) {
    selectedFile.value = file;
    previewUrl.value = URL.createObjectURL(file);
  }
};

const handleSubmit = async () => {
  if (!isEditing.value && !selectedFile.value) {
    alert('請選擇一張公告圖片');
    return;
  }

  submitting.value = true;
  const fd = new FormData();
  fd.append('title', form.value.title);
  fd.append('description', form.value.description || '');
  fd.append('sort_order', form.value.sort_order);
  if (selectedFile.value) {
    fd.append('file', selectedFile.value);
  }

  try {
    if (isEditing.value) {
      await updateAnnouncement(editingId.value, fd);
      alert('公告已更新！');
    } else {
      await createAnnouncement(fd);
      alert('公告已新增！');
    }
    showModal.value = false;
    fetchAnnouncements();
  } catch (e) {
    console.error(e);
    alert('操作失敗：' + (e.response?.data?.detail || '請稍後再試'));
  } finally {
    submitting.value = false;
  }
};

const handleDelete = async (id) => {
  if (!confirm('確定要刪除此公告嗎？此操作無法復原。')) return;
  try {
    await deleteAnnouncement(id);
    alert('公告已刪除');
    fetchAnnouncements();
  } catch (e) {
    console.error(e);
    alert('刪除失敗');
  }
};

onMounted(fetchAnnouncements);
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-announcements {
  color: $text-primary;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;

    h2 { color: $primary-light; margin: 0; }

    @media (max-width: 768px) {
      flex-direction: column;
      align-items: stretch;
      gap: 1rem;

      h2 {
        background-color: rgba($primary-color, 0.1);
        padding: 0.8rem;
        border-radius: $border-radius;
        text-align: center;
        border-left: 4px solid $primary-color;
      }

      .btn {
        width: 100%;
      }
    }
  }

  .loading, .empty {
    text-align: center;
    padding: 3rem;
    color: $text-disabled;
  }

  .ann-grid {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .ann-card {
    display: flex;
    align-items: center;
    gap: 1.2rem;
    background-color: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    padding: 0.8rem;
    transition: opacity 0.2s;

    &.inactive { opacity: 0.5; }

    .ann-image {
      width: 160px;
      height: 90px;
      object-fit: cover;
      border-radius: $border-radius;
      flex-shrink: 0;
    }

    .ann-body {
      flex: 1;
      h3 { margin: 0 0 0.3rem; color: $primary-light; font-size: 1rem; }
      p { margin: 0 0 0.3rem; color: $text-secondary; font-size: 0.9rem; }
      .meta { color: $text-disabled; font-size: 0.8rem; }
    }

    .ann-actions {
      display: flex;
      gap: 0.5rem;
      flex-shrink: 0;
    }
  }

  .btn {
    padding: 0.4rem 0.9rem;
    border: 1px solid $primary-color;
    background: transparent;
    color: $primary-color;
    border-radius: $border-radius;
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.2s;
    &:hover { background: $primary-color; color: #fff; }
  }

  .btn-primary {
    background: $primary-color;
    color: #fff;
    border: none;
    padding: 0.5rem 1.2rem;
    font-weight: bold;
    &:hover { background: $primary-dark; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }

  .btn-danger {
    border-color: #ff6b6b;
    color: #ff6b6b;
    &:hover { background: #ff6b6b; color: #fff; }
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6);
    z-index: 1000;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .modal {
    background: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: 8px;
    padding: 2rem;
    width: 550px;
    max-width: 90%;
    max-height: 90vh;
    overflow-y: auto;

    h3 { color: $primary-light; margin: 0 0 1rem; }

    .form-group {
      margin-bottom: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;

      label { color: $text-secondary; font-weight: 600; font-size: 0.9rem; }

      input[type="text"], input[type="number"], textarea {
        padding: 0.7rem;
        background: $background-color;
        border: 1px solid $medium-grey;
        border-radius: $border-radius;
        color: $text-primary;
        font-size: 0.95rem;
        &:focus { outline: none; border-color: $primary-color; }
      }

      input[type="file"] {
        color: $text-secondary;
        font-size: 0.9rem;
      }

      .tip {
        color: $text-disabled;
        font-size: 0.8rem;
      }
    }

    .preview {
      margin-bottom: 1rem;
      img {
        width: 100%;
        border-radius: $border-radius;
        border: 1px solid $medium-grey;
      }
    }

    .form-actions {
      display: flex;
      gap: 0.8rem;
      justify-content: flex-end;

      .btn-outline {
        padding: 0.5rem 1.2rem;
        background: transparent;
        border: 1px solid $medium-grey;
        color: $text-secondary;
        border-radius: $border-radius;
        cursor: pointer;
        &:hover { background: $medium-grey; }
      }
    }
  }
}
</style>
