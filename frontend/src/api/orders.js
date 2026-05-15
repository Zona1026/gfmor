import api from './index';

/**
 * 取得特定使用者的所有訂單紀錄
 * @param {string} googleId - 使用者的 Google ID
 */
export const getUserOrders = async (googleId) => {
  return await api.get(`/orders/user/${googleId}`);
};
