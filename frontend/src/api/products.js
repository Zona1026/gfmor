// src/api/products.js

import apiClient from './index';

/**
 * 獲取商品列表
 * @param {object} params - 查詢參數，例如 { skip: 0, limit: 10 }
 * @returns {Promise}
 */
export const getProducts = (params) => {
  return apiClient.get('/products/', { params });
};

/**
 * 根據 ID 獲取單一商品
 * @param {number|string} productId - 商品 ID
 * @returns {Promise}
 */
export const getProductById = (productId) => {
  return apiClient.get(`/products/${productId}`);
};

/**
 * 建立新商品
 * @param {object} productData - 商品資料
 * @returns {Promise}
 */
export const createProduct = (productData) => {
  return apiClient.post('/products/', productData);
};

// 其他與商品相關的 API 函式 (更新、刪除) 可以繼續加在這裡
