<template>
  <div class="settings-view">
    <div class="section-header">
      <h2>系統全域設定</h2>
      <button @click="saveSettings" class="btn btn-primary" :disabled="saving">
        <span v-if="saving" class="spinner"></span>
        {{ saving ? '儲存中...' : '儲存變更' }}
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loader"></div>
      <p>正在載入設定...</p>
    </div>

    <div v-else class="settings-grid">
      <div class="settings-card">
        <div class="card-header">
          <span class="icon">🏢</span>
          <h3>基本資訊</h3>
        </div>
        <div class="form-group">
          <label>商店名稱</label>
          <input v-model="editData.store_name" type="text" placeholder="例如：炬烽騎士精品" />
          <p class="help-text">這會影響網頁標題、頁尾以及首頁歡迎詞。</p>
        </div>
        <div class="form-group">
          <label>店面地址</label>
          <input v-model="editData.store_address" type="text" placeholder="請輸入完整地址" />
        </div>
        <div class="form-group">
          <label>聯絡電話</label>
          <input v-model="editData.store_phone" type="text" placeholder="例如：07-1234567" />
        </div>
      </div>

      <div class="settings-card">
        <div class="card-header">
          <span class="icon">⏰</span>
          <h3>營運資訊</h3>
        </div>
        <div class="form-group">
          <label>頁尾描述</label>
          <textarea v-model="editData.footer_description" rows="4" placeholder="顯示在頁尾簡介區塊的文字"></textarea>
          <p class="help-text">簡短介紹您的店面服務特點。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue';
import { useSiteStore } from '../../store/site';
import { storeToRefs } from 'pinia';

const siteStore = useSiteStore();
const { settings, loading } = storeToRefs(siteStore);

const editData = reactive({
  store_name: '',
  store_address: '',
  store_phone: '',
  business_hours: '',
  footer_description: ''
});

const saving = ref(false);

const loadData = async () => {
  await siteStore.fetchSettings();
  Object.assign(editData, settings.value);
};

const saveSettings = async () => {
  saving.value = true;
  try {
    const success = await siteStore.updateSettings(editData);
    if (success) {
      alert('設定已成功更新！');
    }
  } catch (error) {
    alert('更新失敗，請檢查網路連線或稍後再試。');
  } finally {
    saving.value = false;
  }
};

onMounted(loadData);
</script>

<style lang="scss" scoped>
@use '../../assets/_variables.scss' as *;

.settings-view {
  animation: fadeIn 0.4s ease-out;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  
  h2 { color: $primary-light; margin: 0; }

  @media (max-width: 768px) {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
    
    h2 {
      background-color: rgba($primary-color, 0.1);
      padding: 0.8rem;
      border-radius: $border-radius;
      text-align: center;
      border-left: 4px solid $primary-color;
    }
    
    .btn { width: 100%; }
  }
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 2rem;

  @media (max-width: 480px) {
    grid-template-columns: 1fr;
  }
}

.settings-card {
  background: linear-gradient(145deg, #2a2a2a, #1f1f1f);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 5px 15px rgba(0,0,0,0.2);

  .card-header {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 0.8rem;

    .icon { font-size: 1.4rem; }
    h3 { margin: 0; color: $primary-light; font-size: 1.2rem; }
  }
}

.form-group {
  margin-bottom: 1.5rem;

  label {
    display: block;
    color: $text-secondary;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
  }

  input, textarea {
    width: 100%;
    padding: 0.8rem 1rem;
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: $text-primary;
    font-size: 1rem;
    transition: all 0.3s;

    &:focus {
      outline: none;
      border-color: $primary-color;
      background-color: rgba(255, 255, 255, 0.1);
      box-shadow: 0 0 10px rgba($primary-color, 0.2);
    }
  }

  .help-text {
    font-size: 0.8rem;
    color: $text-disabled;
    margin-top: 0.4rem;
  }
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 5rem;
  color: $text-disabled;
}

.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background-color: $primary-color;
  color: #fff;
  border: none;
  padding: 0.8rem 1.5rem;
  border-radius: 8px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;

  &:hover:not(:disabled) {
    background-color: $primary-dark;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba($primary-color, 0.3);
  }

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.loader {
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-top: 4px solid $primary-color;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
