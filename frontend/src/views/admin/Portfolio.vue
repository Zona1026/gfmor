<template>
  <div class="admin-portfolio">
    <div class="section-header">
      <h2>作品集管理</h2>
      <button class="btn btn-primary" @click="openCreateModal">＋ 新增作品</button>
    </div>

    <!-- 分類篩選 -->
    <div class="filter-bar">
      <button 
        v-for="cat in categories" :key="cat.id"
        class="filter-btn" 
        :class="{ active: filterCategory === cat.id }"
        @click="filterCategory = cat.id"
      >{{ cat.label }}</button>
      <button class="filter-btn" :class="{ active: filterCategory === '' }" @click="filterCategory = ''">全部</button>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else class="portfolio-grid">
      <div v-for="item in filteredItems" :key="item.id" class="portfolio-card">
        <img :src="item.image_url" :alt="item.title" class="card-image" />
        <div class="card-body">
          <span class="category-tag">{{ getCategoryLabel(item.category) }}</span>
          <h3>{{ item.title }}</h3>
          <p v-if="item.description" class="desc">{{ item.description }}</p>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" @click="openEditModal(item)">編輯</button>
          <button class="btn btn-sm btn-danger" @click="handleDelete(item.id)">刪除</button>
        </div>
      </div>
      <div v-if="filteredItems.length === 0" class="empty">此分類下尚無作品。</div>
    </div>

    <!-- 新增 / 編輯 Modal -->
    <div class="modal-overlay" v-if="showModal" @click.self="showModal = false">
      <div class="modal">
        <h3>{{ isEditing ? '編輯作品' : '新增作品' }}</h3>
        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label>作品標題</label>
            <input type="text" v-model="form.title" required placeholder="例如：FORCE 2.0 全車改裝" />
          </div>
          <div class="form-group">
            <label>分類</label>
            <select v-model="form.category" required>
              <option value="" disabled>請選擇分類</option>
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>作品描述 (選填)</label>
            <textarea v-model="form.description" rows="4" placeholder="改裝項目、使用零件等..."></textarea>
          </div>
          <div class="form-group">
            <label>{{ isEditing ? '更換圖片 (不換則留空)' : '上傳作品圖片' }}</label>
            <input type="file" accept="image/*" @change="onFileChange" />
          </div>

          <!-- 即時預覽 -->
          <div v-if="previewUrl" class="preview-section">
            <h4>預覽</h4>
            <div class="preview-card">
              <img :src="previewUrl" alt="Preview" class="preview-image" />
              <div class="preview-body">
                <span class="category-tag" v-if="form.category">{{ getCategoryLabel(form.category) }}</span>
                <h3>{{ form.title || '作品標題' }}</h3>
                <p v-if="form.description">{{ form.description }}</p>
              </div>
            </div>
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
import { ref, computed, onMounted } from 'vue';
import { getPortfolioItems, createPortfolioItem, updatePortfolioItem, deletePortfolioItem } from '../../api/admin';

const categories = [
  { id: 'level-1', label: '大改 (5-10萬)' },
  { id: 'level-2', label: '爆改 (10-30萬)' },
  { id: 'level-3', label: 'VVIP (30-50萬)' },
  { id: 'level-4', label: 'SVIP (50萬+)' }
];

const items = ref([]);
const loading = ref(false);
const filterCategory = ref('');
const showModal = ref(false);
const isEditing = ref(false);
const editingId = ref(null);
const submitting = ref(false);
const previewUrl = ref('');
const selectedFile = ref(null);

const form = ref({ title: '', category: '', description: '' });

const filteredItems = computed(() => {
  if (!filterCategory.value) return items.value;
  return items.value.filter(i => i.category === filterCategory.value);
});

const getCategoryLabel = (catId) => {
  return categories.find(c => c.id === catId)?.label || catId;
};

const fetchItems = async () => {
  loading.value = true;
  try {
    items.value = await getPortfolioItems();
  } catch (e) {
    console.error('載入作品集失敗', e);
  } finally {
    loading.value = false;
  }
};

const openCreateModal = () => {
  isEditing.value = false;
  editingId.value = null;
  form.value = { title: '', category: '', description: '' };
  previewUrl.value = '';
  selectedFile.value = null;
  showModal.value = true;
};

const openEditModal = (item) => {
  isEditing.value = true;
  editingId.value = item.id;
  form.value = { title: item.title, category: item.category, description: item.description || '' };
  previewUrl.value = item.image_url;
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
    alert('請選擇一張作品圖片');
    return;
  }
  submitting.value = true;
  const fd = new FormData();
  fd.append('title', form.value.title);
  fd.append('category', form.value.category);
  fd.append('description', form.value.description || '');
  if (selectedFile.value) fd.append('file', selectedFile.value);

  try {
    if (isEditing.value) {
      await updatePortfolioItem(editingId.value, fd);
      alert('作品已更新！');
    } else {
      await createPortfolioItem(fd);
      alert('作品已新增！');
    }
    showModal.value = false;
    fetchItems();
  } catch (e) {
    console.error(e);
    alert('操作失敗：' + (e.response?.data?.detail || '請稍後再試'));
  } finally {
    submitting.value = false;
  }
};

const handleDelete = async (id) => {
  if (!confirm('確定要刪除此作品嗎？此操作無法復原。')) return;
  try {
    await deletePortfolioItem(id);
    alert('作品已刪除');
    fetchItems();
  } catch (e) {
    console.error(e);
    alert('刪除失敗');
  }
};

onMounted(fetchItems);
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-portfolio {
  color: $text-primary;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    h2 { color: $primary-light; margin: 0; }
  }

  .filter-bar {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 1.5rem;

    .filter-btn {
      padding: 0.4rem 1rem;
      border: 1px solid $medium-grey;
      background: transparent;
      color: $text-secondary;
      border-radius: 20px;
      cursor: pointer;
      font-size: 0.85rem;
      transition: all 0.2s;

      &.active {
        background: $primary-color;
        border-color: $primary-color;
        color: #fff;
      }
      &:hover:not(.active) { border-color: $light-grey; }
    }
  }

  .loading, .empty { text-align: center; padding: 3rem; color: $text-disabled; }

  .portfolio-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.2rem;
  }

  .portfolio-card {
    background: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    flex-direction: column;

    .card-image {
      width: 100%;
      height: 200px;
      object-fit: cover;
    }

    .card-body {
      padding: 1rem;
      flex: 1;

      .category-tag {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        background: rgba($primary-color, 0.15);
        color: $primary-color;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
      }

      h3 { margin: 0 0 0.3rem; color: $text-primary; font-size: 1rem; }
      .desc { margin: 0; color: $text-secondary; font-size: 0.85rem; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    }

    .card-actions {
      padding: 0.8rem 1rem;
      border-top: 1px solid $medium-grey;
      display: flex;
      gap: 0.5rem;
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
    background: $primary-color; color: #fff; border: none;
    padding: 0.5rem 1.2rem; font-weight: bold;
    &:hover { background: $primary-dark; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }

  .btn-danger {
    border-color: #ff6b6b; color: #ff6b6b;
    &:hover { background: #ff6b6b; color: #fff; }
  }

  /* Modal */
  .modal-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6); z-index: 1000;
    display: flex; justify-content: center; align-items: center;
  }

  .modal {
    background: $dark-grey; border: 1px solid $medium-grey;
    border-radius: 8px; padding: 2rem; width: 600px;
    max-width: 90%; max-height: 90vh; overflow-y: auto;

    h3 { color: $primary-light; margin: 0 0 1rem; }

    .form-group {
      margin-bottom: 1rem;
      display: flex; flex-direction: column; gap: 0.4rem;

      label { color: $text-secondary; font-weight: 600; font-size: 0.9rem; }

      input[type="text"], textarea, select {
        padding: 0.7rem; background: $background-color;
        border: 1px solid $medium-grey; border-radius: $border-radius;
        color: $text-primary; font-size: 0.95rem;
        &:focus { outline: none; border-color: $primary-color; }
      }

      select { cursor: pointer; }

      input[type="file"] { color: $text-secondary; font-size: 0.9rem; }
    }

    .preview-section {
      margin-bottom: 1rem;
      h4 { color: $text-secondary; margin: 0 0 0.6rem; }
    }

    .preview-card {
      border: 1px solid $medium-grey;
      border-radius: 8px;
      overflow: hidden;
      background: $dark-grey;

      .preview-image { width: 100%; max-height: 300px; object-fit: cover; }

      .preview-body {
        padding: 1rem;

        .category-tag {
          display: inline-block;
          padding: 0.15rem 0.6rem;
          background: rgba($primary-color, 0.15);
          color: $primary-color;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 600;
          margin-bottom: 0.5rem;
        }

        h3 { margin: 0 0 0.3rem; color: $text-primary; }
        p { margin: 0; color: $text-secondary; font-size: 0.9rem; }
      }
    }

    .form-actions {
      display: flex; gap: 0.8rem; justify-content: flex-end;

      .btn-outline {
        padding: 0.5rem 1.2rem; background: transparent;
        border: 1px solid $medium-grey; color: $text-secondary;
        border-radius: $border-radius; cursor: pointer;
        &:hover { background: $medium-grey; }
      }
    }
  }
}
</style>
