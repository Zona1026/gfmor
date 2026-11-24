import { reactive, toRefs } from 'vue';
import { defineStore } from 'pinia';
import { useAuthStore } from './auth';
import { getAdminPreferences, updateAdminPreferences } from '../api/admin';
import { applyAdminTheme, createAdminThemeController } from '../utils/adminTheme';

export const useAdminThemeStore = defineStore('adminTheme', () => {
  const auth = useAuthStore();
  const state = reactive({ theme: 'dark', saving: false, loading: false, error: '' });
  let storage;
  try { storage = window.localStorage; } catch { /* Keep account-backed preferences available without a browser cache. */ }
  const controller = createAdminThemeController({
    state, storage, apply: applyAdminTheme,
    read: token => getAdminPreferences(token),
    write: (theme, token) => updateAdminPreferences(theme, token),
    saved: (username, theme) => {
      if (auth.adminUser?.username === username) auth.setAdminUser({ ...auth.adminUser, theme_preference: theme });
    },
  });
  return { ...toRefs(state), ...controller };
});
