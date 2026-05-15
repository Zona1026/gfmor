import api from './index';

/**
 * 取得特定使用者的所有預約紀錄
 * @param {string} googleId - 使用者的 Google ID
 */
export const getUserBookings = async (googleId) => {
  return await api.get(`/bookings/user/${googleId}`);
};

/**
 * 建立新預約單
 */
export const createBooking = async (bookingData) => {
  return await api.post('/bookings/', bookingData);
};

/**
 * 取得特定日期的所有 PENDING 預約紀錄
 */
export const getDailyBookings = async (dateStr) => {
  return await api.get(`/bookings/date/${dateStr}`);
};

/**
 * 更新預約單 (包含取消預約)
 */
export const updateBooking = async (bookingId, bookingData) => {
  return await api.put(`/bookings/${bookingId}`, bookingData);
};
