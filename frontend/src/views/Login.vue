<template>
  <div class="login-page">
    <div class="login-section">
      <h2>會員登入</h2>
      <div v-if="isInAppBrowser" class="browser-warning">
        <p class="warning-title">目前瀏覽器不支援 Google 登入</p>
        <p class="warning-text">
          請用 Chrome 或 Safari 開啟此頁面，再進行會員登入。
        </p>
        <div class="warning-actions">
          <button type="button" class="btn-copy-link" @click="copyCurrentUrl">
            複製網址
          </button>
          <button type="button" class="btn-secondary" @click="recheckBrowser">
            我已用 Chrome/Safari 開啟，重新檢查
          </button>
        </div>
        <p v-if="copyMessage" class="copy-message">{{ copyMessage }}</p>
      </div>
      <div v-else class="login-options">
        <GoogleLogin :callback="handleLogin" />
      </div>
    </div>

    <div class="divider"></div>

    <div class="login-section">
      <h2>店家登入</h2>
      <div v-if="!showAdminForm" class="login-options">
        <button class="btn-admin-login" @click="showAdminForm = true">登入</button>
      </div>
      <form v-else class="admin-login-form" @submit.prevent="handleAdminSubmit">
        <div class="form-group">
          <input type="text" v-model="adminForm.username" placeholder="帳號" required />
        </div>
        <div class="form-group">
          <input type="password" v-model="adminForm.password" placeholder="密碼" required />
        </div>
        <div class="form-actions">
          <button type="submit" class="btn-admin-submit">確認登入</button>
          <button type="button" class="btn-cancel" @click="showAdminForm = false">取消</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { GoogleLogin } from 'vue3-google-login';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../store/auth';
import { loginWithGoogle } from '../api/auth';
import { loginAdmin } from '../api/admin';

const router = useRouter();
const authStore = useAuthStore();

const inAppBrowserPattern = /Line|FBAN|FBAV|Instagram|Messenger|MicroMessenger/i;

const showAdminForm = ref(false);
const adminForm = ref({ username: '', password: '' });
const copyMessage = ref('');
const isInAppBrowser = ref(inAppBrowserPattern.test(navigator.userAgent || ''));

const copyWithFallback = (text) => {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.setAttribute('readonly', '');
  textArea.style.position = 'fixed';
  textArea.style.top = '-9999px';
  textArea.style.left = '-9999px';
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    return document.execCommand('copy');
  } finally {
    document.body.removeChild(textArea);
  }
};

const copyCurrentUrl = async () => {
  const currentUrl = window.location.href;
  copyMessage.value = '';

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(currentUrl);
    } else if (!copyWithFallback(currentUrl)) {
      throw new Error('copy command failed');
    }

    copyMessage.value = '網址已複製，請貼到 Chrome 或 Safari 開啟。';
  } catch (error) {
    console.error('複製網址失敗:', error);
    copyMessage.value = `無法自動複製，請手動複製網址：${currentUrl}`;
  }
};

const recheckBrowser = () => {
  isInAppBrowser.value = inAppBrowserPattern.test(navigator.userAgent || '');

  if (isInAppBrowser.value) {
    copyMessage.value = '目前仍是內建瀏覽器，請改用 Chrome 或 Safari 開啟。';
    return;
  }

  copyMessage.value = '';
  window.location.reload();
};

const handleLogin = async (response) => {
  const idToken = response.credential;
  try {
    const res = await loginWithGoogle(idToken);
    
    const { access_token, user } = res;

    // 使用 store action 更新狀態
    authStore.setToken(access_token);
    authStore.setUser(user);

    // 檢查資料是否完整，若不完整則導向完善會員資訊頁面
    if (!user.phone || !user.motors || user.motors.length === 0) {
      router.push('/profile/complete');
    } else {
      // 登入成功，導向首頁
      router.push('/');
    }

  } catch (error) {
    console.error('登入失敗:', error);
    alert('Google 登入失敗。若您是從 LINE、Instagram 或 Facebook 開啟，請改用 Chrome 或 Safari 開啟網站後再登入。');
  }
};

const handleAdminSubmit = async () => {
  if (adminForm.value.username && adminForm.value.password) {
    try {
      const res = await loginAdmin(adminForm.value);
      authStore.setAdminToken(res.access_token);
      authStore.setAdminUser({ username: res.username, full_name: res.full_name, role: res.role });
      alert('管理員登入成功！');
      router.push('/admin');
    } catch (error) {
      console.error('管理員登入失敗:', error);
      alert(error.response?.data?.detail || '登入失敗，請確認帳號密碼。');
    }
  }
};
</script>

<style lang="scss" scoped>
@import '../assets/_variables.scss';

.login-page {
  padding: 2rem;
  max-width: 400px;
  margin: 5rem auto;
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  background-color: $dark-grey;
  text-align: center;

  .login-section {
    padding: 1.5rem 0;
  }

  .divider {
    height: 1px;
    background-color: $medium-grey;
    margin: 1rem 0;
  }

  h2 {
    color: $primary-light;
    margin-bottom: 1rem;
  }

  .admin-desc {
    color: $text-secondary;
    font-size: 0.9rem;
    margin-bottom: 1rem;
  }

  .login-options {
    margin-top: 1rem;
    display: flex;
    justify-content: center;
  }

  .browser-warning {
    margin-top: 1rem;
    padding: 1rem;
    border: 1px solid rgba($primary-color, 0.45);
    border-radius: $border-radius;
    background-color: rgba($background-color, 0.55);
    color: $text-primary;
    text-align: left;

    .warning-title {
      color: $primary-light;
      font-size: 1rem;
      font-weight: bold;
      margin-bottom: 0.5rem;
      text-align: center;
    }

    .warning-text {
      color: $text-secondary;
      font-size: 0.95rem;
      line-height: 1.6;
      margin-bottom: 1rem;
      text-align: center;
    }

    .warning-actions {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .btn-copy-link,
    .btn-secondary {
      width: 100%;
      border-radius: $border-radius;
      font-size: 0.95rem;
      font-weight: bold;
      padding: 0.8rem 1rem;
      cursor: pointer;
      transition: 0.3s;
    }

    .btn-copy-link {
      background-color: $primary-color;
      border: 1px solid $primary-color;
      color: $background-color;

      &:hover {
        background-color: $primary-dark;
        border-color: $primary-dark;
      }
    }

    .btn-secondary {
      background-color: transparent;
      border: 1px solid $medium-grey;
      color: $text-primary;

      &:hover {
        background-color: rgba(255, 255, 255, 0.08);
      }
    }

    .copy-message {
      color: $text-secondary;
      font-size: 0.85rem;
      line-height: 1.5;
      margin-top: 0.8rem;
      overflow-wrap: anywhere;
      text-align: center;
    }
  }

  .admin-login-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-top: 1rem;

    .form-group {
      input {
        width: 100%;
        padding: 0.8rem;
        border-radius: $border-radius;
        border: 1px solid $medium-grey;
        background-color: $background-color;
        color: $text-primary;
        font-size: 1rem;

        &:focus {
          outline: none;
          border-color: $primary-color;
        }
      }
    }

    .form-actions {
      display: flex;
      gap: 1rem;
      justify-content: center;

      .btn-admin-submit {
        background-color: $primary-color;
        color: $background-color;
        border: none;
        padding: 0.8rem 1.5rem;
        border-radius: $border-radius;
        font-size: 1rem;
        font-weight: bold;
        cursor: pointer;
        transition: 0.3s;
        
        &:hover {
          background-color: $primary-dark;
        }
      }

      .btn-cancel {
        background-color: transparent;
        color: $text-secondary;
        border: 1px solid $medium-grey;
        padding: 0.8rem 1.5rem;
        border-radius: $border-radius;
        font-size: 1rem;
        cursor: pointer;
        transition: 0.3s;
        
        &:hover {
          background-color: rgba(255, 255, 255, 0.1);
        }
      }
    }
  }

  .btn-admin-login {
    background-color: transparent;
    color: $primary-color;
    border: 1px solid $primary-color;
    padding: 0.8rem 1.5rem;
    border-radius: $border-radius;
    font-size: 1rem;
    font-weight: bold;
    cursor: pointer;
    transition: 0.3s;
    
    &:hover {
      background-color: rgba($primary-color, 0.1);
    }
  }
}
</style>
