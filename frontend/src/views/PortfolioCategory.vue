<template>
  <div class="portfolio-category-page">
    <h1>{{ categoryName }}</h1>
    <p class="subtitle">{{ categoryDesc }}</p>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else-if="items.length" class="project-grid">
      <router-link 
        v-for="item in items" :key="item.id" 
        :to="`/portfolio/project/${item.id}`" 
        class="project-card"
      >
        <img :src="item.image_url" :alt="item.title" />
        <div class="project-info">
          <h3>{{ item.title }}</h3>
        </div>
      </router-link>
    </div>

    <div v-else class="empty">此分類下尚無作品，敬請期待！</div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import api from '../api/index';

const route = useRoute();

const categoryMap = {
  'level-1': { name: '大改車主作品集', desc: '消費 5-10 萬' },
  'level-2': { name: '爆改車主作品集', desc: '消費 10-30 萬' },
  'level-3': { name: '爆改車主之VVIP作品集', desc: '消費 30-50 萬' },
  'level-4': { name: '爆改車主之SVIP作品集', desc: '消費 50 萬以上' }
};

const items = ref([]);
const loading = ref(false);
const categoryName = ref('');
const categoryDesc = ref('');

const fetchItems = async (category) => {
  loading.value = true;
  const info = categoryMap[category] || { name: '作品集', desc: '' };
  categoryName.value = info.name;
  categoryDesc.value = info.desc;
  
  try {
    items.value = await api.get(`/portfolio/category/${category}`);
  } catch (e) {
    console.error('載入作品集失敗', e);
    items.value = [];
  } finally {
    loading.value = false;
  }
};

onMounted(() => fetchItems(route.params.category));
watch(() => route.params.category, (newCat) => { if (newCat) fetchItems(newCat); });
</script>

<style lang="scss" scoped>
@import '../assets/_variables.scss';

.portfolio-category-page {
  padding: 2rem;
  text-align: center;
}

h1 {
  color: $primary-color;
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: $text-disabled;
  margin-bottom: 2rem;
}

.loading, .empty {
  padding: 3rem;
  color: $text-disabled;
  font-size: 1.1rem;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.project-card {
  background-color: #2c2c2c;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  transition: transform 0.3s ease;
  text-decoration: none;
  color: inherit;

  &:hover {
    transform: translateY(-5px);
  }

  img {
    width: 100%;
    height: 220px;
    object-fit: cover;
  }

  .project-info {
    padding: 1rem;
  }

  h3 {
    color: $primary-color;
    margin: 0;
    font-size: 1.2rem;
  }
}
</style>
