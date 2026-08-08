<template>
  <div class="admin-reset-page">
    <section class="reset-panel">
      <p class="eyebrow">店家後台</p>
      <h1>重設密碼</h1>
      <p class="subtitle">
        請設定新的管理員密碼。
      </p>

      <div v-if="!token" class="status-message error">
        重設連結缺少 token，請重新申請重設密碼。
      </div>

      <form v-else-if="!isCompleted" class="reset-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="new-password">新密碼</label>
          <input
            id="new-password"
            type="password"
            v-model="form.password"
            autocomplete="new-password"
            minlength="8"
            required
            placeholder="至少 8 個字元"
          />
        </div>
        <div class="form-group">
          <label for="confirm-password">確認新密碼</label>
          <input
            id="confirm-password"
            type="password"
            v-model="form.confirmPassword"
            autocomplete="new-password"
            minlength="8"
            required
            placeholder="再次輸入新密碼"
          />
        </div>

        <p v-if="message" class="status-message error">{{ message }}</p>

        <button type="submit" class="btn-submit" :disabled="isSubmitting">
          {{ isSubmitting ? '更新中...' : '更新密碼' }}
        </button>
      </form>

      <div v-else class="status-message success">
        密碼已更新，請使用新密碼登入。
      </div>

      <router-link class="back-login" to="/admin-login">回店家登入</router-link>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { confirmAdminPasswordReset } from '../api/admin';

const route = useRoute();
const token = computed(() => String(route.query.token || ''));

const form = ref({
  password: '',
  confirmPassword: ''
});
const isSubmitting = ref(false);
const isCompleted = ref(false);
const message = ref('');

const handleSubmit = async () => {
  message.value = '';
  if (form.value.password.length < 8) {
    message.value = '新密碼至少需要 8 個字元';
    return;
  }
  if (form.value.password !== form.value.confirmPassword) {
    message.value = '兩次輸入的新密碼不一致';
    return;
  }

  isSubmitting.value = true;
  try {
    await confirmAdminPasswordReset({
      token: token.value,
      password: form.value.password
    });
    isCompleted.value = true;
    form.value = { password: '', confirmPassword: '' };
  } catch (error) {
    console.error('重設管理員密碼失敗:', error);
    message.value = error.response?.data?.detail || '重設連結無效或已過期';
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style lang="scss" scoped>
@use '../assets/_variables.scss' as *;

.admin-reset-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background:
    linear-gradient(135deg, rgba(229, 57, 53, 0.16), transparent 36%),
    $background-color;
}

.reset-panel {
  width: min(100%, 420px);
  padding: 2rem;
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  background: $dark-grey;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
}

.eyebrow {
  margin: 0 0 0.4rem;
  color: $primary-light;
  font-size: 0.9rem;
  font-weight: 700;
}

h1 {
  margin: 0;
  color: $text-primary;
  font-size: 1.8rem;
}

.subtitle {
  margin: 0.75rem 0 1.6rem;
  color: $text-secondary;
  line-height: 1.6;
}

.reset-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

  label {
    color: $text-secondary;
    font-size: 0.9rem;
  }

  input {
    width: 100%;
    padding: 0.85rem;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    background: $background-color;
    color: $text-primary;
    font-size: 1rem;

    &:focus {
      outline: none;
      border-color: $primary-color;
      box-shadow: 0 0 0 3px rgba(229, 57, 53, 0.18);
    }
  }
}

.btn-submit,
.back-login {
  min-height: 42px;
  border-radius: $border-radius;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: $transition-base;
}

.btn-submit {
  width: 100%;
  border: 1px solid $primary-color;
  background: $primary-color;
  color: $background-color;

  &:hover {
    background: $primary-dark;
    border-color: $primary-dark;
  }

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
}

.back-login {
  display: grid;
  place-items: center;
  width: 100%;
  margin-top: 1rem;
  border: 1px solid $medium-grey;
  color: $text-secondary;
  text-decoration: none;

  &:hover {
    color: $text-primary;
    border-color: $light-grey;
  }
}

.status-message {
  padding: 0.9rem 1rem;
  border-radius: $border-radius;
  line-height: 1.6;
  font-size: 0.95rem;

  &.error {
    border: 1px solid rgba(#ff4d4f, 0.4);
    background: rgba(#ff4d4f, 0.08);
    color: #ff9c9c;
  }

  &.success {
    border: 1px solid rgba(#52c41a, 0.4);
    background: rgba(#52c41a, 0.1);
    color: #95de64;
  }
}

@media (max-width: 520px) {
  .reset-panel {
    padding: 1.25rem;
  }
}
</style>
