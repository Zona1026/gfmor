<template>
  <div class="products-page">
    <h2>商品列表</h2>

    <!-- 篩選 -->
    <div class="filter-bar">
      <input type="text" v-model="searchKeyword" placeholder="搜尋商品..." class="search-input" />
      <select v-model="filterCategory" class="category-select">
        <option value="">全部分類</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>
    </div>

    <div v-if="isLoading" class="loading-state">
      <div class="loader-spinner"></div>
      <p>正在載入商品資料...</p>
    </div>
    <div v-if="error" class="error-state">
      <span class="error-icon">⚠️</span>
      <p>{{ error }}</p>
    </div>

    <div v-if="!isLoading && !error" class="product-grid">
      <div v-for="product in filteredProducts" :key="product.id" class="product-card">
        <div class="card-image-wrap">
          <img v-if="product.image_url" :src="product.image_url" :alt="product.name" class="card-image" @load="imageLoaded($event)" />
          <div v-else class="card-image placeholder-img"><span>暫無圖片</span></div>
          <div class="image-skeleton"></div>
        </div>
        <div class="card-body">
          <span class="category-tag" v-if="product.category">{{ product.category }}</span>
          <h3>{{ product.name }}</h3>
          <p class="description" v-if="product.description">{{ product.description }}</p>
        </div>
        <div class="card-footer">
          <div class="price-info">
            <span class="price">NT$ {{ product.price?.toLocaleString() }}</span>
            <span class="stock" :class="{ 'out': product.stock <= 0 }">
              {{ product.stock > 0 ? `庫存 ${product.stock}` : '已售完' }}
            </span>
          </div>
          <button 
            class="btn-add-cart" 
            :disabled="product.stock <= 0"
            @click="handleAddToCart(product)"
          >
            {{ product.stock <= 0 ? '已售完' : '加入購物車' }}
          </button>
        </div>
      </div>
      <div v-if="filteredProducts.length === 0" class="empty-state">
        <div class="empty-icon">🔍</div>
        <p>查無符合條件的商品。</p>
        <button class="btn-clear-filter" @click="searchKeyword = ''; filterCategory = '';">清除篩選</button>
      </div>
    </div>

    <!-- 加入成功提示 -->
    <transition name="toast">
      <div v-if="showToast" class="toast">✓ 已加入購物車</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useProductsStore } from '../store/products';
import { useCartStore } from '../store/cart';
import { storeToRefs } from 'pinia';

const productsStore = useProductsStore();
const cartStore = useCartStore();
const { isLoading, error, items } = storeToRefs(productsStore);

const searchKeyword = ref('');
const filterCategory = ref('');
const showToast = ref(false);

// 只顯示上架中的商品
const activeProducts = computed(() => items.value.filter(p => p.is_active));

const categories = computed(() => {
  const cats = new Set(activeProducts.value.map(p => p.category).filter(Boolean));
  return [...cats];
});

const imageLoaded = (event) => {
  event.target.classList.add('is-loaded');
};

const filteredProducts = computed(() => {
  let list = activeProducts.value;
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase();
    list = list.filter(p => p.name.toLowerCase().includes(kw) || (p.description || '').toLowerCase().includes(kw));
  }
  if (filterCategory.value) {
    list = list.filter(p => p.category === filterCategory.value);
  }
  return list;
});

const handleAddToCart = (product) => {
  cartStore.addItem(product);
  showToast.value = true;
  setTimeout(() => showToast.value = false, 1500);
};

onMounted(() => {
  productsStore.fetchProducts();
});
</script>

<style lang="scss" scoped>
@import '../assets/_variables.scss';

.products-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 1rem auto;

  h2 { color: $primary-light; margin-bottom: 1.5rem; text-align: center; font-size: 2.2rem; text-shadow: 0 2px 10px rgba(0,0,0,0.5); }

  .filter-bar {
    display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; justify-content: center;

    .search-input, .category-select {
      padding: 0.8rem 1.2rem; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 30px; color: $text-primary; font-size: 1rem; transition: $transition-base;
      backdrop-filter: blur(5px);
      &::placeholder { color: $text-disabled; }
      &:focus { outline: none; border-color: $primary-color; box-shadow: 0 0 10px rgba($primary-color, 0.3); background: rgba(255, 255, 255, 0.1); }
    }
    .search-input { flex: 1; max-width: 400px; }
    .category-select { cursor: pointer; min-width: 160px; 
      option { background: $dark-grey; color: $text-primary; }
    }
  }

  .loading-state, .error-state, .empty-state {
    text-align: center; padding: 4rem 2rem; color: $text-disabled; font-size: 1.2rem;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem;
  }
  
  .loader-spinner {
    width: 40px; height: 40px; border: 4px solid rgba($primary-color, 0.3);
    border-top: 4px solid $primary-color; border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

  .error-state { color: #ff6b6b; background: rgba(#ff6b6b, 0.1); border: 1px solid rgba(#ff6b6b, 0.3); border-radius: $border-radius; }
  .error-icon { font-size: 2rem; }
  
  .empty-icon { font-size: 3rem; margin-bottom: 0.5rem; opacity: 0.5; }
  .btn-clear-filter {
    margin-top: 1rem; padding: 0.6rem 1.5rem; background: transparent; border: 1px solid $primary-color;
    color: $primary-color; border-radius: 20px; cursor: pointer; transition: $transition-base;
    &:hover { background: rgba($primary-color, 0.1); }
  }

  .product-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 2rem;
  }

  .product-card {
    background: linear-gradient(145deg, #2a2a2a, #1f1f1f); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px;
    overflow: hidden; display: flex; flex-direction: column; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    
    &:hover { 
      transform: translateY(-8px) scale(1.02); 
      box-shadow: 0 15px 30px rgba(0,0,0,0.4), 0 0 15px rgba($primary-color, 0.2);
      border-color: rgba($primary-color, 0.3);
      
      .card-image-wrap .card-image { transform: scale(1.1); }
    }

    .card-image-wrap {
      position: relative; overflow: hidden; height: 220px;
      
      .image-skeleton {
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: linear-gradient(90deg, #2c2c2c 25%, #3a3a3a 50%, #2c2c2c 75%);
        background-size: 200% 100%; animation: loading 1.5s infinite; z-index: 1;
      }
      
      .card-image { 
        width: 100%; height: 100%; object-fit: cover; display: block; 
        transition: transform 0.5s ease; position: relative; z-index: 2; opacity: 0;
        &.is-loaded { opacity: 1; }
        &.is-loaded ~ .image-skeleton { display: none; }
      }
      .placeholder-img {
        width: 100%; height: 100%; background: $medium-grey; position: relative; z-index: 2;
        display: flex; align-items: center; justify-content: center; color: $text-disabled;
        ~ .image-skeleton { display: none; }
      }
    }

    .card-body {
      padding: 1.5rem; flex: 1;
      .category-tag {
        display: inline-block; padding: 0.2rem 0.8rem; background: rgba($primary-color, 0.15);
        color: $primary-color; border-radius: 20px; font-size: 0.75rem; font-weight: 700; margin-bottom: 0.8rem;
        letter-spacing: 0.5px;
      }
      h3 { margin: 0 0 0.5rem; color: $text-primary; font-size: 1.15rem; line-height: 1.4; }
      .description { margin: 0; color: $text-disabled; font-size: 0.9rem;
        display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
      }
    }

    .card-footer {
      padding: 1.2rem 1.5rem; border-top: 1px solid rgba(255,255,255,0.05); background: rgba(0,0,0,0.2);
      display: flex; justify-content: space-between; align-items: center;

      .price-info {
        display: flex; flex-direction: column; gap: 0.2rem;
        .price { font-weight: 800; color: #fff; font-size: 1.2rem; text-shadow: 0 0 10px rgba(255,255,255,0.2); }
        .stock { color: $text-disabled; font-size: 0.8rem; &.out { color: #ff6b6b; } }
      }

      .btn-add-cart {
        padding: 0.6rem 1.2rem; background: $primary-color; color: #fff; border: none;
        border-radius: 25px; cursor: pointer; font-weight: bold; font-size: 0.9rem; transition: $transition-base;
        box-shadow: 0 4px 10px rgba($primary-color, 0.4);
        position: relative; overflow: hidden;
        
        &:hover:not(:disabled) { 
          background: $primary-light; transform: translateY(-2px);
          box-shadow: 0 6px 15px rgba($primary-color, 0.6);
        }
        &:active:not(:disabled) { transform: translateY(0); }
        &:disabled { opacity: 0.5; cursor: not-allowed; background: $medium-grey; box-shadow: none; }
      }
    }
  }

  @keyframes loading { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

  .toast {
    position: fixed; bottom: 2rem; left: 50%; transform: translateX(-50%);
    background: rgba(33, 33, 33, 0.9); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1);
    color: #fff; padding: 1rem 2.5rem; border-radius: 30px;
    font-weight: bold; z-index: 9999; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    display: flex; align-items: center; gap: 0.8rem;
    &::before { content: '🛒'; font-size: 1.2rem; }
  }
  .toast-enter-active, .toast-leave-active { transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
  .toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(40px) scale(0.9); }
}
</style>
