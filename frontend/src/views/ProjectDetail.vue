<template>
  <div class="project-detail-page">
    <div v-if="loading" class="loading">載入中...</div>
    <div v-else-if="item">
      <h1>{{ item.title }}</h1>
      <div class="project-content">
        <img :src="item.image_url" :alt="item.title" />
        <div class="project-details">
          <h2>作品資訊</h2>
          <div class="info-row">
            <strong>分類：</strong>
            <span>{{ getCategoryLabel(item.category) }}</span>
          </div>
          <div class="info-row" v-if="item.description">
            <strong>描述：</strong>
            <span>{{ item.description }}</span>
          </div>
          <div class="info-row">
            <strong>上傳日期：</strong>
            <span>{{ formatDate(item.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="empty">找不到該作品。</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import api from '../api/index';

const route = useRoute();
const item = ref(null);
const loading = ref(false);

const categoryMap = {
  'level-1': '大改 (5-10萬)',
  'level-2': '爆改 (10-30萬)',
  'level-3': 'VVIP (30-50萬)',
  'level-4': 'SVIP (50萬+)'
};

const getCategoryLabel = (catId) => categoryMap[catId] || catId;

const formatDate = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getDate()).padStart(2,'0')}`;
};

onMounted(async () => {
  loading.value = true;
  try {
    item.value = await api.get(`/portfolio/${route.params.id}`);
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
});
</script>

<style lang="scss" scoped>
@import '../assets/_variables.scss';

.project-detail-page {
  padding: 2rem;
  max-width: 960px;
  margin: 0 auto;
}

h1 {
  color: $primary-color;
  font-size: 2.5rem;
  margin-bottom: 2rem;
  text-align: center;
}

.loading, .empty {
  text-align: center;
  padding: 3rem;
  color: $text-disabled;
  font-size: 1.1rem;
}

.project-content {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;

  @media (min-width: 768px) {
    grid-template-columns: 2fr 1fr;
  }

  img {
    width: 100%;
    border-radius: 8px;
  }

  .project-details {
    background-color: #2c2c2c;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);

    h2 {
      color: $primary-color;
      margin-top: 0;
      margin-bottom: 1.5rem;
      border-bottom: 1px solid $primary-color;
      padding-bottom: 0.8rem;
    }

    .info-row {
      font-size: 1.05rem;
      color: $text-secondary;
      margin-bottom: 1rem;
      line-height: 1.6;

      strong {
        color: $primary-color;
        margin-right: 0.5rem;
      }
    }
  }
}
</style>
