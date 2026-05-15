<template>
  <div class="admin-products">
    <div class="section-header">
      <h2>商城管理</h2>
      <button class="btn btn-primary" @click="openCreateModal">＋ 新增商品</button>
    </div>

    <!-- 篩選 -->
    <div class="filter-bar">
      <input type="text" v-model="searchKeyword" placeholder="搜尋商品名稱..." class="search-input" />
      <button class="filter-btn" :class="{ active: filterStatus === '' }" @click="filterStatus = ''">全部</button>
      <button class="filter-btn" :class="{ active: filterStatus === 'active' }" @click="filterStatus = 'active'">上架中</button>
      <button class="filter-btn" :class="{ active: filterStatus === 'inactive' }" @click="filterStatus = 'inactive'">已下架</button>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else class="product-grid">
      <div v-for="product in filteredProducts" :key="product.id" class="product-card" :class="{ inactive: !product.is_active }">
        <div class="card-image-wrap">
          <img v-if="product.image_url" :src="product.image_url" :alt="product.name" class="card-image" />
          <div v-else class="card-image placeholder-img">
            <span>無圖片</span>
          </div>
          <span class="status-badge" :class="product.is_active ? 'on' : 'off'">
            {{ product.is_active ? '上架中' : '已下架' }}
          </span>
        </div>
        <div class="card-body">
          <h3>{{ product.name }}</h3>
          <div class="price-stock">
            <span class="price">NT$ {{ product.price?.toLocaleString() }}</span>
            <span class="stock">庫存 {{ product.stock }}</span>
          </div>
          <p v-if="product.category" class="cat">{{ product.category }}</p>
        </div>
        <div class="card-actions">
          <button class="btn btn-sm" @click="handleToggle(product)">
            {{ product.is_active ? '下架' : '上架' }}
          </button>
          <button class="btn btn-sm" @click="openEditModal(product)">編輯</button>
          <button class="btn btn-sm btn-danger" @click="handleDelete(product.id)">刪除</button>
        </div>
      </div>
      <div v-if="filteredProducts.length === 0" class="empty">查無符合條件的商品。</div>
    </div>

    <!-- 新增 / 編輯 Modal -->
    <div class="modal-overlay" v-if="showModal" @click.self="showModal = false">
      <div class="modal">
        <h3>{{ isEditing ? '編輯商品' : '新增商品' }}</h3>
        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label>商品名稱</label>
            <input type="text" v-model="form.name" required />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>價格 (NT$)</label>
              <input type="number" v-model.number="form.price" required min="0" />
            </div>
            <div class="form-group">
              <label>庫存數量</label>
              <input type="number" v-model.number="form.stock" required min="0" />
            </div>
          </div>
          <div class="form-group">
            <label>分類 (選填)</label>
            <input type="text" v-model="form.category" placeholder="例如：排氣管、車殼、輪胎" />
          </div>
          <div class="form-group">
            <label>商品描述 (選填)</label>
            <textarea v-model="form.description" rows="3" placeholder="商品簡介..."></textarea>
          </div>
          <div class="form-group">
            <label>{{ isEditing ? '更換商品圖片 (不換則留空)' : '上傳商品圖片' }}</label>
            <input type="file" accept="image/*" @change="onFileChange" />
          </div>
          <div v-if="previewUrl" class="preview">
            <img :src="previewUrl" alt="preview" />
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="showModal = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              {{ submitting ? '處理中...' : (isEditing ? '更新' : '新增') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { getProducts, createProduct, updateProduct, deleteProduct, toggleProductActive } from '../../api/admin';

const products = ref([]);
const loading = ref(false);
const searchKeyword = ref('');
const filterStatus = ref('');
const showModal = ref(false);
const isEditing = ref(false);
const editingId = ref(null);
const submitting = ref(false);
const previewUrl = ref('');
const selectedFile = ref(null);

const form = ref({ name: '', price: 0, stock: 0, category: '', description: '' });

const filteredProducts = computed(() => {
  let list = products.value;
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase();
    list = list.filter(p => p.name.toLowerCase().includes(kw));
  }
  if (filterStatus.value === 'active') list = list.filter(p => p.is_active);
  if (filterStatus.value === 'inactive') list = list.filter(p => !p.is_active);
  return list;
});

const fetchProducts = async () => {
  loading.value = true;
  try { products.value = await getProducts(); }
  catch (e) { console.error('載入商品失敗', e); }
  finally { loading.value = false; }
};

const openCreateModal = () => {
  isEditing.value = false; editingId.value = null;
  form.value = { name: '', price: 0, stock: 0, category: '', description: '' };
  previewUrl.value = ''; selectedFile.value = null;
  showModal.value = true;
};

const openEditModal = (p) => {
  isEditing.value = true; editingId.value = p.id;
  form.value = { name: p.name, price: p.price, stock: p.stock, category: p.category || '', description: p.description || '' };
  previewUrl.value = p.image_url || '';
  selectedFile.value = null;
  showModal.value = true;
};

const onFileChange = (e) => {
  const file = e.target.files[0];
  if (file) { selectedFile.value = file; previewUrl.value = URL.createObjectURL(file); }
};

const handleSubmit = async () => {
  submitting.value = true;
  const fd = new FormData();
  fd.append('name', form.value.name);
  fd.append('price', form.value.price);
  fd.append('stock', form.value.stock);
  fd.append('description', form.value.description || '');
  fd.append('category', form.value.category || '');
  if (selectedFile.value) fd.append('file', selectedFile.value);

  try {
    if (isEditing.value) { await updateProduct(editingId.value, fd); alert('商品已更新！'); }
    else { await createProduct(fd); alert('商品已新增！'); }
    showModal.value = false; fetchProducts();
  } catch (e) { console.error(e); alert('操作失敗'); }
  finally { submitting.value = false; }
};

const handleToggle = async (p) => {
  try {
    await toggleProductActive(p.id);
    p.is_active = p.is_active ? 0 : 1;
  } catch (e) { console.error(e); alert('切換失敗'); }
};

const handleDelete = async (id) => {
  if (!confirm('確定要永久刪除此商品嗎？')) return;
  try { await deleteProduct(id); alert('商品已刪除'); fetchProducts(); }
  catch (e) { console.error(e); alert('刪除失敗'); }
};

onMounted(fetchProducts);
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-products {
  color: $text-primary;

  .section-header {
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;
    h2 { color: $primary-light; margin: 0; }
  }

  .filter-bar {
    display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.5rem; align-items: center;

    .search-input {
      padding: 0.5rem 1rem; background: $background-color; border: 1px solid $medium-grey;
      border-radius: $border-radius; color: $text-primary; font-size: 0.9rem; width: 220px;
      &::placeholder { color: $text-disabled; }
      &:focus { outline: none; border-color: $primary-color; }
    }

    .filter-btn {
      padding: 0.4rem 1rem; border: 1px solid $medium-grey; background: transparent;
      color: $text-secondary; border-radius: 20px; cursor: pointer; font-size: 0.85rem; transition: all 0.2s;
      &.active { background: $primary-color; border-color: $primary-color; color: #fff; }
      &:hover:not(.active) { border-color: $light-grey; }
    }
  }

  .loading, .empty { text-align: center; padding: 3rem; color: $text-disabled; }

  .product-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1.2rem;
  }

  .product-card {
    background: $dark-grey; border: 1px solid $medium-grey; border-radius: 8px;
    overflow: hidden; display: flex; flex-direction: column; transition: opacity 0.2s;
    &.inactive { opacity: 0.55; }

    .card-image-wrap {
      position: relative;
      .card-image { width: 100%; height: 200px; object-fit: cover; display: block; }
      .placeholder-img {
        width: 100%; height: 200px; background: $medium-grey;
        display: flex; align-items: center; justify-content: center; color: $text-disabled;
      }
      .status-badge {
        position: absolute; top: 8px; right: 8px; padding: 0.2rem 0.6rem;
        border-radius: 12px; font-size: 0.7rem; font-weight: bold;
        &.on { background: #4caf50; color: #fff; }
        &.off { background: #ff6b6b; color: #fff; }
      }
    }

    .card-body {
      padding: 1rem; flex: 1;
      h3 { margin: 0 0 0.5rem; color: $text-primary; font-size: 1rem; }
      .price-stock {
        display: flex; justify-content: space-between; margin-bottom: 0.3rem;
        .price { color: $primary-color; font-weight: bold; font-size: 1.05rem; }
        .stock { color: $text-disabled; font-size: 0.85rem; }
      }
      .cat { margin: 0; color: $text-disabled; font-size: 0.8rem; }
    }

    .card-actions {
      padding: 0.8rem 1rem; border-top: 1px solid $medium-grey;
      display: flex; gap: 0.5rem;
    }
  }

  .btn {
    padding: 0.4rem 0.9rem; border: 1px solid $primary-color; background: transparent;
    color: $primary-color; border-radius: $border-radius; cursor: pointer; font-size: 0.85rem; transition: all 0.2s;
    &:hover { background: $primary-color; color: #fff; }
  }

  .btn-primary {
    background: $primary-color; color: #fff; border: none; padding: 0.5rem 1.2rem; font-weight: bold;
    &:hover { background: $primary-dark; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }

  .btn-danger {
    border-color: #ff6b6b; color: #ff6b6b;
    &:hover { background: #ff6b6b; color: #fff; }
  }

  .modal-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6); z-index: 1000;
    display: flex; justify-content: center; align-items: center;
  }

  .modal {
    background: $dark-grey; border: 1px solid $medium-grey;
    border-radius: 8px; padding: 2rem; width: 550px;
    max-width: 90%; max-height: 90vh; overflow-y: auto;

    h3 { color: $primary-light; margin: 0 0 1rem; }

    .form-row { display: flex; gap: 1rem; }
    .form-row .form-group { flex: 1; }

    .form-group {
      margin-bottom: 1rem; display: flex; flex-direction: column; gap: 0.4rem;
      label { color: $text-secondary; font-weight: 600; font-size: 0.9rem; }
      input[type="text"], input[type="number"], textarea, select {
        padding: 0.7rem; background: $background-color; border: 1px solid $medium-grey;
        border-radius: $border-radius; color: $text-primary; font-size: 0.95rem;
        &:focus { outline: none; border-color: $primary-color; }
      }
      input[type="file"] { color: $text-secondary; font-size: 0.9rem; }
    }

    .preview {
      margin-bottom: 1rem;
      img { width: 100%; border-radius: $border-radius; border: 1px solid $medium-grey; }
    }

    .form-actions {
      display: flex; gap: 0.8rem; justify-content: flex-end;
      .btn-outline {
        padding: 0.5rem 1.2rem; background: transparent; border: 1px solid $medium-grey;
        color: $text-secondary; border-radius: $border-radius; cursor: pointer;
        &:hover { background: $medium-grey; }
      }
    }
  }
}
</style>
