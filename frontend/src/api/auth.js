import api from './index';

/**
 * 使用 Google 的 ID Token 向後端進行登入或註冊
 * @param {string} googleToken - 從 Google 獲取的 ID Token
 * @returns {Promise} - 回傳一個包含後端 JWT 和使用者資訊的 Promise
 */
export const loginWithGoogle = (googleToken) => {
  // 注意：後端需要一個接收 Google token 的端點，這裡暫定為 /auth/google
  // 您需要根據您的後端 API.md 文件進行調整
  return api.post('/auth/google', { token: googleToken });
};
