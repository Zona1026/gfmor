import api from './index';

/**
 * 管理員登入
 * @param {Object} credentials { username, password }
 */
export const loginAdmin = async (credentials) => {
  const response = await api.post('/admin/login', credentials);
  return response;
};

export const getAdminBookings = async (params) => {
  return await api.get('/bookings', { params });
};

export const forceCreateBooking = async (bookingData) => {
  return await api.post('/admin/bookings', bookingData);
};

export const closeTimeslot = async (booking_time) => {
  return await api.post('/admin/bookings/close', { booking_time });
};

export const updateBookingStatus = async (booking_id, updateData) => {
  return await api.put(`/bookings/${booking_id}`, updateData);
};

export const searchUsersByName = async (name) => {
  return await api.get('/users/search', { params: { name } });
};

export const getMembers = async (skip = 0, limit = 200) => {
  return await api.get('/users/', { params: { skip, limit } });
};

export const updateMemberNotes = async (google_id, admin_notes) => {
  return await api.put(`/users/${google_id}`, { admin_notes });
};

// ======= 公告管理 =======
export const getAnnouncements = async () => {
  return await api.get('/announcements/all');
};

export const createAnnouncement = async (formData) => {
  return await api.post('/announcements/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

export const updateAnnouncement = async (id, formData) => {
  return await api.put(`/announcements/${id}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

export const deleteAnnouncement = async (id) => {
  return await api.delete(`/announcements/${id}`);
};

// ======= 作品集管理 =======
export const getPortfolioItems = async () => {
  return await api.get('/portfolio/');
};

export const createPortfolioItem = async (formData) => {
  return await api.post('/portfolio/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

export const updatePortfolioItem = async (id, formData) => {
  return await api.put(`/portfolio/${id}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

export const deletePortfolioItem = async (id) => {
  return await api.delete(`/portfolio/${id}`);
};

// ======= 商品管理 =======
export const getProducts = async () => {
  return await api.get('/products/');
};

export const createProduct = async (formData) => {
  return await api.post('/products/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

export const updateProduct = async (id, formData) => {
  return await api.put(`/products/${id}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

export const deleteProduct = async (id) => {
  return await api.delete(`/products/${id}`);
};

export const toggleProductActive = async (id) => {
  return await api.patch(`/products/${id}/toggle`);
};

// ======= 訂單管理 =======
export const getAllOrders = async () => {
  return await api.get('/orders/');
};

export const createInstoreOrder = async (data) => {
  return await api.post('/orders/admin', data);
};

export const updateOrderStatus = async (id, status) => {
  return await api.patch(`/orders/${id}/status?status=${encodeURIComponent(status)}`);
};

export const updateInstoreOrder = async (id, data) => {
  return await api.put(`/orders/${id}`, data);
};

export const cancelOrder = async (id) => {
  return await api.patch(`/orders/${id}/cancel`);
};

// ======= 管理員帳號管理 =======
export const getAdmins = async () => {
  return await api.get('/admins/');
};

export const createAdmin = async (data) => {
  return await api.post('/admins/', data);
};

export const deleteAdmin = async (id) => {
  return await api.delete(`/admins/${id}`);
};

export const updateAdmin = async (id, data) => {
  return await api.put(`/admins/${id}`, data);
};
