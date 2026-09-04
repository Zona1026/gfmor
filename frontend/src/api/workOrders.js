import api from './index';

export const getUserWorkOrders = async (googleId) => {
  return await api.get(`/work-orders/user/${googleId}`);
};
