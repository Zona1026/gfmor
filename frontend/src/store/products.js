// src/store/products.js

import { defineStore } from 'pinia';
import { ref } from 'vue';
import { getPaginatedProducts } from '../api/products';

// 使用 defineStore 定義一個名為 'products' 的 store
// 第一個參數是 store 的唯一 ID
export const useProductsStore = defineStore('products', () => {
  // --- State ---
  // ref() 用於定義響應式狀態，相當於 Options API 中的 data
  
  // 儲存商品列表
  const items = ref([]);
  // 標示目前是否正在從 API 載入資料
  const isLoading = ref(false);
  // 儲存載入過程中發生的錯誤
  const error = ref(null);
  const total = ref(0);
  const page = ref(1);
  const totalPages = ref(1);

  // --- Actions ---
  // 在 Composition API 風格的 store 中，Actions 就是可以直接呼叫的函式

  /**
   * 從 API 獲取商品列表並更新 state
   */
  async function fetchProducts({ requestedPage = 1, search = '', categoryId = '' } = {}) {
    // 開始載入，將 isLoading 設為 true
    isLoading.value = true;
    // 將先前的錯誤清除
    error.value = null;

    try {
      const result = await getPaginatedProducts({
        page: requestedPage,
        page_size: 50,
        search: search || undefined,
        category_id: categoryId || undefined,
        status: 'active',
      });
      items.value = result.items;
      total.value = result.total;
      page.value = result.page;
      totalPages.value = result.total_pages;
    } catch (err) {
      // 如果發生錯誤，將錯誤訊息存入 error
      console.error('獲取商品資料失敗:', err);
      error.value = '無法載入商品資料，請稍後再試。';
    } finally {
      // 無論成功或失敗，最後都結束載入狀態
      isLoading.value = false;
    }
  }

  // --- Getters ---
  // 在 Composition API 風格中，Getters 可以被 computed 屬性取代，
  // 但為了方便，也可以直接回傳。
  // 此處我們暫時不需要 Getters，可以直接從 state (items) 讀取資料。

  // 將 state 和 actions 回傳，這樣在組件中才能使用它們
  return {
    items,
    isLoading,
    error,
    total,
    page,
    totalPages,
    fetchProducts,
  };
});
