import { defineStore } from 'pinia';
import { ref } from 'vue';

export const ADMIN_IDLE_TIMEOUT_MS = 60 * 60 * 1000;
const ADMIN_LAST_ACTIVITY_KEY = 'adminLastActivityAt';

const safeParse = (key) => {
  try {
    const val = localStorage.getItem(key);
    if (!val || val === 'undefined') return null;
    return JSON.parse(val);
  } catch (e) {
    return null;
  }
};

export const useAuthStore = defineStore('auth', () => {
  // 一般使用者
  const token = ref(localStorage.getItem('token') || null);
  const user = ref(safeParse('user'));

  // 管理員
  const adminToken = ref(localStorage.getItem('adminToken') || null);
  const adminUser = ref(safeParse('adminUser'));

  function setAdminActivity(timestamp = Date.now()) {
    localStorage.setItem(ADMIN_LAST_ACTIVITY_KEY, String(timestamp));
  }

  function isAdminSessionIdle(now = Date.now()) {
    if (!adminToken.value) return false;
    const lastActivityAt = Number(localStorage.getItem(ADMIN_LAST_ACTIVITY_KEY));
    if (!Number.isFinite(lastActivityAt) || lastActivityAt <= 0) return true;
    return now - lastActivityAt > ADMIN_IDLE_TIMEOUT_MS;
  }

  function setToken(newToken) {
    token.value = newToken;
    localStorage.setItem('token', newToken);
  }

  function setUser(newUser) {
    user.value = newUser;
    localStorage.setItem('user', JSON.stringify(newUser));
  }

  function logout() {
    token.value = null;
    user.value = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  function setAdminToken(newToken) {
    adminToken.value = newToken;
    localStorage.setItem('adminToken', newToken);
    setAdminActivity();
  }

  function setAdminUser(newUser) {
    adminUser.value = newUser;
    localStorage.setItem('adminUser', JSON.stringify(newUser));
  }

  function adminLogout() {
    adminToken.value = null;
    adminUser.value = null;
    localStorage.removeItem('adminToken');
    localStorage.removeItem('adminUser');
    localStorage.removeItem(ADMIN_LAST_ACTIVITY_KEY);
  }

  return { 
    token, user, setToken, setUser, logout,
    adminToken,
    adminUser,
    setAdminToken,
    setAdminUser,
    setAdminActivity,
    isAdminSessionIdle,
    adminLogout
  };
});
