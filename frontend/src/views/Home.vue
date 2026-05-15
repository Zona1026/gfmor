<template>
  <div class="home-page">
    <h1>歡迎來到 GFmotor</h1>
    <p>您的機車改裝與維修專家</p>

    <!-- 公告輪播 (Carousel) -->
    <div class="announcements-section">
      <div class="carousel" v-if="displaySlides.length">
        <div class="carousel-track">
          <transition name="fade" mode="out-in">
            <div class="event-card" :key="currentSlide">
              <div v-if="displaySlides[currentSlide].placeholder" class="event-image placeholder-image">
                <span>16:9 公告圖片預覽區</span>
              </div>
              <img v-else :src="displaySlides[currentSlide].image_url" :alt="displaySlides[currentSlide].title" class="event-image" />
              <div class="event-content">
                <h2 class="event-title">{{ displaySlides[currentSlide].title }}</h2>
                <p class="event-description" v-if="displaySlides[currentSlide].description">{{ displaySlides[currentSlide].description }}</p>
              </div>
            </div>
          </transition>
        </div>
        <!-- 小圓點切換 -->
        <div class="carousel-dots" v-if="displaySlides.length > 1">
          <span 
            v-for="(_, idx) in displaySlides" 
            :key="idx" 
            class="dot" 
            :class="{ active: idx === currentSlide }" 
            @click="goToSlide(idx)"
          ></span>
        </div>
      </div>
    </div>

    <div class="portfolio-section">
      <h2>作品集</h2>
      <div class="portfolio-categories">
        <router-link v-for="category in portfolioCategories" :key="category.name" :to="`/portfolio/${category.id}`" class="portfolio-category-card">
          <h3>{{ category.name }}</h3>
          <p>{{ category.description }}</p>
        </router-link>
      </div>
    </div>

    <div class="content-row">
      <div class="business-hours">
        <h3>營業時間</h3>
        <ul>
          <li v-for="item in businessHours" :key="item.day">
            <strong>{{ item.day }}:</strong> <span>{{ item.time }}</span>
          </li>
        </ul>
      </div>

      <div class="social-links">
        <h3>關注我們</h3>
        <ul>
          <li v-for="link in socialLinks" :key="link.name">
            <a :href="link.url" target="_blank" rel="noopener noreferrer">
              <img :src="link.icon" :alt="link.name" />
            </a>
          </li>
        </ul>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import api from '../api/index';
// 匯入圖示
import facebookIcon from '../assets/icons/facebook.svg';
import instagramIcon from '../assets/icons/instagram.svg';
import threadsIcon from '../assets/icons/threads.svg';
import lineIcon from '../assets/icons/line.svg';

// 公告資料
const announcements = ref([]);
const currentSlide = ref(0);
let autoplayTimer = null;

// 如果沒有公告，顯示佔位卡片
const placeholderSlides = [
  { id: 'p1', title: '公告標題預覽', description: '這裡會顯示您在後台上傳的公告內容，上傳後此區塊將自動替換。', placeholder: true },
  { id: 'p2', title: '第二則公告預覽', description: '多則公告時可用下方小圓點切換瀏覽。', placeholder: true }
];

const displaySlides = computed(() => {
  return announcements.value.length > 0 ? announcements.value : placeholderSlides;
});

const goToSlide = (idx) => {
  currentSlide.value = idx;
  resetAutoplay();
};

const nextSlide = () => {
  currentSlide.value = (currentSlide.value + 1) % displaySlides.value.length;
};

const resetAutoplay = () => {
  if (autoplayTimer) clearInterval(autoplayTimer);
  if (displaySlides.value.length > 1) {
    autoplayTimer = setInterval(nextSlide, 8000);
  }
};

const fetchAnnouncements = async () => {
  try {
    const data = await api.get('/announcements/');
    announcements.value = data || [];
    currentSlide.value = 0;
    resetAutoplay();
  } catch (e) {
    console.error('無法載入公告', e);
    resetAutoplay();
  }
};

onMounted(fetchAnnouncements);
onUnmounted(() => { if (autoplayTimer) clearInterval(autoplayTimer); });

// 作品集分類
const portfolioCategories = ref([
  { id: 'level-1', name: '大改車主作品集', description: '( 消費5-10萬 )' },
  { id: 'level-2', name: '爆改車主作品集', description: '( 消費10-30萬 )' },
  { id: 'level-3', name: '爆改車主之VVIP作品集', description: '( 消費30-50萬 )' },
  { id: 'level-4', name: '爆改車主之SVIP作品集', description: '( 消費50萬以上 )' }
]);

// 營業時間資料
const businessHours = ref([
  { day: '平日', time: '13:00 ~ 22:00' },
  { day: '週六', time: '11:00 ~ 22:00' },
  { day: '週日', time: '不定時營業 (不接預約)' }
]);

// 社群媒體網址
const socialLinks = ref([
  { name: 'Facebook', url: 'https://www.facebook.com/gf.motor', icon: facebookIcon },
  { name: 'Instagram', url: 'https://www.instagram.com/gjufengmotor/', icon: instagramIcon },
  { name: 'Threads', url: 'https://www.threads.com/@gjufengmotor', icon: threadsIcon },
  { name: 'Official LINE', url: 'https://lin.ee/23mk4EM', icon: lineIcon }
]);
</script>

<style lang="scss" scoped>
@import '../assets/_variables.scss';

.home-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 80vh; 
  padding: 2rem; // Use padding on the main container
  text-align: center;
}

h1 {
  color: $primary-color;
  margin-bottom: 1rem;
  font-size: 3rem;
}

p {
  font-size: 1.2rem;
  color: $text-secondary;
}

.event-card {
  background: linear-gradient(145deg, #2a2a2a, #1f1f1f);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  text-align: left;
}

.announcements-section {
  width: 90%;
  max-width: 850px;
  margin-top: 2.5rem;
}

.carousel {
  position: relative;

  .carousel-track {
    width: 100%;
  }

  .carousel-dots {
    display: flex;
    justify-content: center;
    gap: 0.6rem;
    margin-top: 1rem;

    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background-color: $medium-grey;
      cursor: pointer;
      transition: all 0.3s;

      &.active {
        background-color: $primary-color;
        transform: scale(1.3);
      }

      &:hover:not(.active) {
        background-color: $light-grey;
      }
    }
  }
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.4s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.placeholder-image {
  aspect-ratio: 16 / 9;
  background-color: $medium-grey;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-disabled;
  font-size: 1.1rem;
  letter-spacing: 0.05em;
}
.event-image {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  display: block; // Removes bottom space under image
}

.event-content {
  padding: 1.5rem 2rem;
}

.event-title {
  color: $text-primary;
  margin-top: 0;
  margin-bottom: 0.75rem;
  font-size: 1.75rem;
  font-family: $font-family-heading;
}

.event-description {
  color: $text-secondary;
  margin: 0;
  font-size: 1.1rem;
}

.portfolio-section {
  width: 90%;
  max-width: 850px;
  margin-top: 2.5rem;
  text-align: center;
}

.portfolio-section h2 {
  color: $primary-color;
  font-size: 2rem;
  margin-bottom: 1.5rem;
}

.portfolio-categories {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.portfolio-category-card {
  background: linear-gradient(145deg, #2a2a2a, #1f1f1f);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 2.5rem 2rem;
  border-radius: 12px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  text-decoration: none;
  color: inherit;
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute; top: 0; left: 0; width: 4px; height: 100%;
    background: $primary-color;
    transform: scaleY(0); transition: transform 0.4s ease; transform-origin: bottom;
  }
}

.portfolio-category-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.4);
  border-color: rgba($primary-color, 0.3);
  
  &::before { transform: scaleY(1); }
  
  h3 { color: $primary-light; }
}

.portfolio-category-card h3 {
  color: $primary-color;
  margin-top: 0;
  margin-bottom: 0.5rem;
  font-size: 1.4rem;
}

.portfolio-category-card p {
  color: $text-secondary;
  margin: 0;
  font-size: 1rem;
}

.content-row {
  display: flex;
  flex-wrap: wrap; // Allows items to stack on smaller screens
  justify-content: center;
  align-items: stretch; // Aligns items to have the same height
  gap: 2.5rem; // Space between the cards
  width: 90%;
  max-width: 850px;
  margin: 2.5rem auto 0;
}

.business-hours {
  margin-top: 0;
  padding: 2rem;
  border-radius: 12px;
  background: linear-gradient(145deg, #2a2a2a, #1f1f1f);
  border: 1px solid rgba(255, 255, 255, 0.05);
  text-align: left;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
  flex: 1;
  min-width: 300px;

  h3 {
    color: $primary-color;
    margin-top: 0;
    margin-bottom: 1.2rem;
    font-size: 1.5rem;
    text-align: center;
    border-bottom: 1px solid #FFC107;
    padding-bottom: 0.8rem;
  }

  ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
  }

  li {
    font-size: 1.1rem;
    color: $text-secondary;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.2rem 0;
  }

  strong {
    color: $primary-color;
    margin-right: 1rem;
    white-space: nowrap;
  }
}

.social-links {
  margin-top: 0;
  padding: 2rem;
  background: linear-gradient(145deg, #2a2a2a, #1f1f1f);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
  flex: 1;
  min-width: 300px;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  // justify-content: center; // Removed for top alignment
  align-items: center;

  h3 {
    color: $primary-color;
    margin-top: 0;
    margin-bottom: 1.5rem; // Increased space
    font-size: 1.5rem;
    border-bottom: 1px solid #FFC107;
    padding-bottom: 0.8rem;
    width: 100%; // Make border span the card
  }

  ul {
    list-style: none;
    padding: 0;
    margin: 0; // Reset margin
    display: flex;
    justify-content: center; // Center the icons within the card
    gap: 1.5rem;
    margin-top: auto; // Pushes the icons to the bottom
    margin-bottom: auto; // Helps center if there's extra space
  }

  a {
    display: block;
    
    img {
      width: 48px;
      height: 48px;
      border-radius: 8px;
      transition: transform 0.3s ease, box-shadow 0.3s ease;

      &:hover {
        transform: scale(1.1);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      }
    }
  }
}
</style>
