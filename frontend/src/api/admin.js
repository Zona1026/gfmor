import api from './index';

const adminAuthConfig = () => {
  const adminToken = localStorage.getItem('adminToken');
  return adminToken ? { headers: { Authorization: `Bearer ${adminToken}` } } : {};
};

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

export const getWorkOrders = async (params = {}) => {
  return await api.get('/work-orders/', { params });
};

export const getWorkOrder = async (id) => {
  return await api.get(`/work-orders/${id}`);
};

export const createWorkOrder = async (data) => {
  return await api.post('/work-orders/', data);
};

export const updateWorkOrder = async (id, data) => {
  return await api.put(`/work-orders/${id}`, data, adminAuthConfig());
};

export const deleteWorkOrder = async (id, data) => {
  return await api.delete(`/work-orders/${id}`, { ...adminAuthConfig(), data });
};

export const addWorkOrderLineItem = async (id, data) => {
  return await api.post(`/work-orders/${id}/line-items`, data);
};

export const addWorkOrderPayment = async (id, data) => {
  return await api.post(`/work-orders/${id}/payments`, data);
};

export const getWorkOrderApprovals = async (params = {}) => {
  return await api.get('/work-orders/approvals/', { params });
};

export const approveWorkOrderApproval = async (id, data = {}) => {
  return await api.post(`/work-orders/approvals/${id}/approve`, data, adminAuthConfig());
};

export const rejectWorkOrderApproval = async (id, data = {}) => {
  return await api.post(`/work-orders/approvals/${id}/reject`, data, adminAuthConfig());
};

export const forceCreateBooking = async (bookingData) => {
  return await api.post('/admin/bookings', bookingData);
};

export const closeTimeslot = async (booking_time) => {
  return await api.post('/admin/bookings/close', { booking_time });
};

export const updateBookingStatus = async (booking_id, updateData) => {
  return await api.put(`/bookings/${booking_id}`, updateData, adminAuthConfig());
};

export const searchUsersByName = async (name) => {
  return await api.get('/users/search', { params: { name } });
};

export const getMembers = async (skip = 0, limit = 200) => {
  return await api.get('/users/', { params: { skip, limit } });
};

export const getCustomers = async (params = {}) => {
  return await api.get('/customers/', { params });
};

export const getCustomerDetail = async (customerType, customerId) => {
  return await api.get(`/customers/${customerType}/${encodeURIComponent(customerId)}`);
};

export const updateMemberNotes = async (google_id, admin_notes) => {
  return await api.put(`/users/${google_id}`, { admin_notes });
};

export const updateGuestCustomer = async (id, data) => {
  return await api.put(`/guest-customers/${id}`, data);
};

export const createGuestMotor = async (guestId, data) => {
  return await api.post(`/customers/guest/${guestId}/motors`, data);
};

export const updateGuestMotor = async (guestId, motorId, data) => {
  return await api.put(`/customers/guest/${guestId}/motors/${motorId}`, data);
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

export const getProductCategories = async (params = {}) => {
  return await api.get('/products/categories/', { params });
};

export const createProductCategory = async (data) => {
  return await api.post('/products/categories/', data);
};

export const updateProductCategory = async (id, data) => {
  return await api.put(`/products/categories/${id}`, data);
};

export const toggleProductCategory = async (id) => {
  return await api.patch(`/products/categories/${id}/toggle`);
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
export const getInventoryItems = async (params = {}) => {
  return await api.get('/admin/inventory/items', { params });
};

export const getInventoryMovements = async () => {
  return await api.get('/admin/inventory/movements');
};

export const getInventoryReservations = async (params = {}) => {
  return await api.get('/admin/inventory/reservations', { params });
};

export const adjustInventory = async (data) => {
  return await api.post('/admin/inventory/adjustments', data);
};

export const releaseInventoryReservation = async (id, data) => {
  return await api.post(`/admin/inventory/reservations/${id}/release`, data);
};

export const scrapInventory = async (data) => {
  return await api.post('/admin/inventory/scrap', data);
};

export const getPurchaseRequests = async (params = {}) => {
  return await api.get('/admin/purchases/', { params });
};

export const getPurchaseRequest = async (id) => {
  return await api.get(`/admin/purchases/${id}`);
};

export const orderPurchaseRequest = async (id, data = {}) => {
  return await api.post(`/admin/purchases/${id}/order`, data);
};

export const receivePurchaseRequest = async (id, data) => {
  return await api.post(`/admin/purchases/${id}/receive`, data);
};

export const assignPurchaseRequest = async (id, data) => {
  return await api.post(`/admin/purchases/${id}/assign`, data);
};

export const cancelPurchaseRequest = async (id, data = {}) => {
  return await api.post(`/admin/purchases/${id}/cancel`, data);
};

export const getAccountingReceipts = async (params = {}) => {
  return await api.get('/admin/accounting/receipts', { params });
};

export const getAccountingRefunds = async (params = {}) => {
  return await api.get('/admin/accounting/refunds', { params });
};

export const createAccountingRefund = async (data) => {
  return await api.post('/admin/accounting/refunds', data);
};

export const getShopReceivables = async (params = {}) => {
  return await api.get('/admin/accounting/shop-receivables', { params });
};

export const getPayables = async (params = {}) => {
  return await api.get('/admin/accounting/payables', { params });
};

export const createPayable = async (data) => {
  return await api.post('/admin/accounting/payables', data);
};

export const addPayablePayment = async (id, data) => {
  return await api.post(`/admin/accounting/payables/${id}/payments`, data);
};

export const updateOrderPaymentStatus = async (id, data) => {
  return await api.patch(`/orders/${id}/payment-status`, data);
};

export const getAllOrders = async () => {
  return await api.get('/orders/');
};

export const getShopOrders = async () => {
  return await api.get('/orders/shop');
};

export const createInstoreOrder = async (data) => {
  return await api.post('/orders/admin', data);
};

export const updateOrderStatus = async (id, status) => {
  return await api.patch(`/orders/${id}/status?status=${encodeURIComponent(status)}`);
};

export const updateOrderItemStatus = async (itemId, status) => {
  return await api.patch(`/orders/items/${itemId}/status`, { status });
};

export const recordOrderItemNotification = async (itemId, data) => {
  return await api.post(`/orders/items/${itemId}/notifications`, data);
};

export const updateInstoreOrder = async (id, data) => {
  return await api.put(`/orders/${id}`, data);
};

export const cancelOrder = async (id) => {
  return await api.patch(`/orders/${id}/cancel`);
};

export const getGuestCustomers = async (q = '') => {
  return await api.get('/guest-customers/', { params: q ? { q } : {} });
};

export const getGuestOrders = async (id) => {
  return await api.get(`/guest-customers/${id}/orders`);
};

export const mergeGuestToMember = async (guestId, googleId) => {
  return await api.post(`/guest-customers/${guestId}/merge`, { google_id: googleId });
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
