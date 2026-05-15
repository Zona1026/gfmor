<template>
  <div class="login-page">
    <div class="login-section">
      <h2>會員登入</h2>
      <div class="login-options">
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

const showAdminForm = ref(false);
const adminForm = ref({ username: '', password: '' });

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
    alert('登入失敗，請稍後再試。');
  }
};

const handleAdminSubmit = async () => {
  if (adminForm.value.username && adminForm.value.password) {
    try {
      const res = await loginAdmin(adminForm.value);
      authStore.setAdminToken(res.access_token);
      authStore.setAdminUser({ username: res.username });
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
