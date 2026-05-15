import api from './index';

/**
 * 取得單一使用者詳細資訊
 * @param {string} googleId - 使用者的 Google ID
 */
export const getUser = async (googleId) => {
  return await api.get(`/users/${googleId}`);
};

/**
 * 更新使用者資訊 (含建立新車籍資料)
 * @param {string} googleId - 使用者的 Google ID 
 * @param {Object} profileData - 要更新的資料 (包含 phone, motors 等)
 */
export const updateUserProfile = async (googleId, profileData) => {
  return await api.put(`/users/${googleId}`, profileData);
};

/**
 * 上傳使用者頭像
 * @param {string} googleId - 使用者的 Google ID
 * @param {FormData} formData - 包含圖片的 FormData
 */
export const uploadAvatar = async (googleId, formData) => {
  return await api.post(`/users/${googleId}/avatar`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};
