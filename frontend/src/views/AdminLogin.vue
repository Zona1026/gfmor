<template>
  <div class="admin-login-page">
    <section class="login-panel">
      <p class="eyebrow">店家後台</p>
      <h1>{{ shopName }}</h1>
      <p class="subtitle">請使用店家管理員帳號登入。</p>

      <form class="admin-login-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="admin-username">帳號</label>
          <input
            id="admin-username"
            type="text"
            v-model.trim="adminForm.username"
            autocomplete="username"
            required
          />
        </div>
        <div class="form-group">
          <label for="admin-password">密碼</label>
          <input
            id="admin-password"
            type="password"
            v-model="adminForm.password"
            autocomplete="current-password"
            required
          />
        </div>
        <button type="submit" class="btn-submit" :disabled="isSubmitting">
          {{ isSubmitting ? '登入中...' : '登入後台' }}
        </button>
      </form>

      <button type="button" class="forgot-button" @click="openForgotModal">
        忘記密碼？
      </button>
      <router-link class="back-home" to="/">返回網站首頁</router-link>
    </section>

    <div v-if="showForgotModal" class="modal-overlay" @click.self="closeForgotModal">
      <div class="modal">
        <h2>自助重設密碼</h2>
        <p class="modal-copy">
          請輸入管理員帳號與已綁定的 Email。若資料相符，系統會寄出一次性重設連結。
        </p>

        <form @submit.prevent="requestPasswordReset">
          <div class="form-group">
            <label for="reset-username">管理員帳號</label>
            <input
              id="reset-username"
              type="text"
              v-model.trim="resetForm.username"
              autocomplete="username"
              placeholder="例如：staff_01"
              required
            />
          </div>
          <div class="form-group">
            <label for="reset-email">綁定 Email</label>
            <input
              id="reset-email"
              type="email"
              v-model.trim="resetForm.email"
              autocomplete="email"
              placeholder="name@example.com"
              required
            />
          </div>

          <p class="modal-hint">
            若此帳號尚未綁定 Email，請先請有權限的管理員補上 Email，或由系統維護人員做第一次重設。
          </p>
          <p v-if="resetMessage" class="reset-message">{{ resetMessage }}</p>

          <div class="modal-actions">
            <button type="button" class="btn-outline" @click="closeForgotModal">關閉</button>
            <button type="submit" class="btn-primary" :disabled="isResetSubmitting">
              {{ isResetSubmitting ? '寄送中...' : '寄送重設連結' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../store/auth';
import { useSiteStore } from '../store/site';
import { loginAdmin, requestAdminPasswordReset } from '../api/admin';

const router = useRouter();
const authStore = useAuthStore();
const siteStore = useSiteStore();
const { settings } = storeToRefs(siteStore);

const adminForm = ref({
  username: '',
  password: ''
});
const resetForm = ref({
  username: '',
  email: ''
});
const isSubmitting = ref(false);
const isResetSubmitting = ref(false);
const showForgotModal = ref(false);
const resetMessage = ref('');

const shopName = computed(() => settings.value.store_name || '炬烽騎士精品');

const handleSubmit = async () => {
  if (!adminForm.value.username || !adminForm.value.password) return;

  isSubmitting.value = true;
  try {
    const res = await loginAdmin(adminForm.value);
    authStore.logout();
    authStore.setAdminToken(res.access_token);
    authStore.setAdminUser({
      username: res.username,
      full_name: res.full_name,
      role: res.role
    });
    router.push('/admin');
  } catch (error) {
    console.error('管理員登入失敗:', error);
    alert(error.response?.data?.detail || '登入失敗，請確認帳號密碼。');
  } finally {
    isSubmitting.value = false;
  }
};

const openForgotModal = () => {
  resetForm.value.username = adminForm.value.username || '';
  resetForm.value.email = '';
  resetMessage.value = '';
  showForgotModal.value = true;
};

const closeForgotModal = () => {
  showForgotModal.value = false;
  resetMessage.value = '';
};

const requestPasswordReset = async () => {
  isResetSubmitting.value = true;
  resetMessage.value = '';
  try {
    const res = await requestAdminPasswordReset(resetForm.value);
    resetMessage.value = res.message || '若資料正確，重設密碼連結已寄出。';
  } catch (error) {
    console.error('申請重設密碼失敗:', error);
    resetMessage.value = error.response?.data?.detail || '重設密碼信件寄送失敗，請稍後再試。';
  } finally {
    isResetSubmitting.value = false;
  }
};

onMounted(() => {
  siteStore.fetchSettings();
});
</script>

<style lang="scss" scoped>
@use '../assets/_variables.scss' as *;

.admin-login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background:
    linear-gradient(135deg, rgba(229, 57, 53, 0.16), transparent 36%),
    $background-color;
}

.login-panel {
  width: min(100%, 420px);
  padding: 2rem;
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  background: $dark-grey;
  text-align: left;
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
  line-height: 1.25;
}

.subtitle {
  margin: 0.75rem 0 1.6rem;
  color: $text-secondary;
  line-height: 1.6;
}

.admin-login-form {
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
.btn-primary,
.btn-outline,
.forgot-button,
.back-home {
  min-height: 42px;
  border-radius: $border-radius;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: $transition-base;
}

.btn-submit,
.btn-primary {
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

.forgot-button {
  width: 100%;
  margin-top: 1rem;
  border: 1px solid transparent;
  background: transparent;
  color: $primary-light;

  &:hover {
    background: rgba(255, 255, 255, 0.06);
  }
}

.back-home {
  display: grid;
  place-items: center;
  width: 100%;
  margin-top: 0.4rem;
  border: 1px solid $medium-grey;
  color: $text-secondary;
  text-decoration: none;

  &:hover {
    color: $text-primary;
    border-color: $light-grey;
  }
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.72);
}

.modal {
  width: min(100%, 460px);
  padding: 1.6rem;
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  background: $dark-grey;

  h2 {
    margin: 0 0 1rem;
    color: $primary-light;
    font-size: 1.35rem;
  }
}

.modal-copy,
.modal-hint,
.reset-message {
  color: $text-secondary;
  line-height: 1.6;
}

.modal-hint {
  margin: 1rem 0 0;
  font-size: 0.85rem;
}

.reset-message {
  margin: 1rem 0 0;
  color: $primary-light;
  font-size: 0.9rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.8rem;
  margin-top: 1.5rem;
}

.btn-outline {
  border: 1px solid $medium-grey;
  background: transparent;
  color: $text-secondary;
  padding: 0 1rem;

  &:hover {
    color: $text-primary;
    background: rgba(255, 255, 255, 0.08);
  }
}

.btn-primary {
  padding: 0 1rem;
}

@media (max-width: 520px) {
  .login-panel,
  .modal {
    padding: 1.25rem;
  }

  .modal-actions {
    flex-direction: column-reverse;
  }

  .btn-outline,
  .btn-primary {
    width: 100%;
  }
}
</style>
