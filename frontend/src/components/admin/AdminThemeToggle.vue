<template>
  <div class="admin-theme-control">
    <div class="theme-options" role="group" aria-label="後台外觀">
      <button v-for="option in options" :key="option.value" type="button" :aria-pressed="theme === option.value"
        :disabled="loading || saving" @click="themeStore.setTheme(option.value)">
        <span aria-hidden="true">{{ option.icon }}</span>{{ option.label }}
      </button>
    </div>
    <small v-if="saving" role="status">正在儲存外觀…</small>
    <small v-if="error" class="theme-error" role="alert">{{ error }} <button type="button" :disabled="loading || saving" @click="themeStore.retry()">重試</button></small>
  </div>
</template>
<script setup>
import { storeToRefs } from 'pinia';
import { useAdminThemeStore } from '../../store/adminTheme';
const themeStore = useAdminThemeStore();
const { theme, saving, loading, error } = storeToRefs(themeStore);
const options = [{ value: 'dark', label: '深色', icon: '☾' }, { value: 'light', label: '淺色', icon: '☀' }];
</script>
<style scoped>
.admin-theme-control { display: grid; gap: 6px; justify-items: end; font-size: 12px; }
.theme-options { display: flex; gap: 3px; padding: 3px; border: 1px solid var(--admin-border, #424242); border-radius: 8px; background: var(--admin-surface, #212121); }
.theme-options button { display: flex; align-items: center; gap: 7px; border: 0; border-radius: 5px; padding: 8px 12px; font: inherit; font-size: 13px; color: var(--admin-muted, #bdbdbd); background: transparent; cursor: pointer; white-space: nowrap; }
.theme-options button[aria-pressed=true] { background: var(--admin-accent, #e53935); color: #fff; }
.theme-options button:focus-visible { outline: 2px solid var(--admin-accent, #ef5350); outline-offset: 2px; }
button:disabled { opacity: .6; cursor: wait; }
small { color: var(--admin-muted, #bdbdbd); }
.theme-error { max-width: 320px; color: var(--admin-danger, #ff6b6b); }
.theme-error button { border: 0; background: none; color: inherit; text-decoration: underline; cursor: pointer; }
@media (max-width: 600px) { .admin-theme-control { justify-items: start; } }
</style>
