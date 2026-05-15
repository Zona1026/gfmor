import api from './index';

/**
 * 根據車籍 ID 更新車籍資訊
 * @param {number} motorId - 車籍 ID
 * @param {Object} motorData - 要更新的資料
 */
export const updateMotor = async (motorId, motorData) => {
  return await api.put(`/motors/${motorId}`, motorData);
};

/**
 * 根據車籍 ID 刪除車籍資料
 * @param {number} motorId - 車籍 ID
 */
export const deleteMotor = async (motorId) => {
  return await api.delete(`/motors/${motorId}`);
};
