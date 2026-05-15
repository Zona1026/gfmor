<template>
  <div class="profile-complete-page">
    <h2>完善會員資訊</h2>
    <p>為了提供更好的服務體驗，請填寫您的基本聯絡方式與車輛資訊。</p>
    <form @submit.prevent="handleSubmit" class="profile-form">
      <div class="form-group">
        <label for="phone">手機號碼 *</label>
        <input type="tel" id="phone" v-model="formData.phone" required pattern="[0-9]{10}" placeholder="例如：0912345678" />
      </div>

      <div class="form-group">
        <label for="license_plate">車牌號碼 *</label>
        <input type="text" id="license_plate" v-model="motorData.license_plate" required placeholder="例如：ABC-1234" />
      </div>

      <div class="form-group">
        <label for="brand">廠牌 *</label>
        <input type="text" id="brand" v-model="motorData.brand" required placeholder="例如：SYM" />
      </div>

      <div class="form-group">
        <label for="model_name">型號 *</label>
        <input type="text" id="model_name" v-model="motorData.model_name" required placeholder="例如：JETS" />
      </div>

      <button type="submit" class="submit-btn" :disabled="isSubmitting">完成設定</button>
    </form>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../store/auth';
import { updateUserProfile } from '../api/users';

const router = useRouter();
const authStore = useAuthStore();

const isSubmitting = ref(false);

const formData = reactive({
  phone: authStore.user?.phone || ''
});

const motorData = reactive({
  license_plate: '',
  brand: '',
  model_name: ''
});

const handleSubmit = async () => {
  if (!authStore.user?.google_id) return;
  
  isSubmitting.value = true;
  try {
    const payload = {
      phone: formData.phone,
      motors: [
        {
          license_plate: motorData.license_plate,
          brand: motorData.brand,
          model_name: motorData.model_name
        }
      ]
    };
    
    // Call API
    // 假設 api.put 自動透過 interceptor 解出 response data
    const updatedUser = await updateUserProfile(authStore.user.google_id, payload);
    
    // Update store
    // 有時候 backend endpoint 會回傳更新後的使用者
    if (updatedUser) {
      authStore.setUser(updatedUser);
    }
    
    alert('會員資訊設定成功！');
    router.push('/');
  } catch (error) {
    console.error('更新會員資訊失敗:', error);
    alert(error.response?.data?.detail || '更新會員資訊失敗，請確認資料後重試。');
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style lang="scss" scoped>
@import '../assets/_variables.scss';

.profile-complete-page {
  padding: 2rem;
  max-width: 500px;
  margin: 5rem auto;
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  background-color: $dark-grey;
  
  h2 {
    color: $primary-light;
    margin-bottom: 1rem;
    text-align: center;
  }
  
  p {
    color: $light-grey;
    text-align: center;
    margin-bottom: 2rem;
  }
  
  .profile-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      
      label {
        color: $light-grey;
        font-weight: bold;
      }
      
      input {
        padding: 0.75rem;
        border: 1px solid $medium-grey;
        border-radius: $border-radius;
        background-color: $background-color;
        color: #fff;
        
        &:focus {
          outline: none;
          border-color: $primary-color;
        }
      }
    }
    
    .submit-btn {
      background-color: $primary-color;
      color: $background-color;
      padding: 1rem;
      border: none;
      border-radius: $border-radius;
      font-weight: bold;
      font-size: 1.1rem;
      cursor: pointer;
      margin-top: 1rem;
      transition: background-color 0.3s;
      
      &:hover {
        background-color: $primary-light;
      }
      
      &:disabled {
        background-color: $medium-grey;
        cursor: not-allowed;
      }
    }
  }
}
</style>
