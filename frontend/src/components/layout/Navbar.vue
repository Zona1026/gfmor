<template>
  <nav class="navbar" :class="{ 'scrolled': isScrolled }">
    <div class="navbar-brand">
      <router-link to="/">GFmotor</router-link>
    </div>
    
    <!-- Hamburger Menu Toggle -->
    <button class="hamburger" @click="toggleMenu" :class="{ 'is-active': isMenuOpen }">
      <span class="bar"></span>
      <span class="bar"></span>
      <span class="bar"></span>
    </button>

    <div class="navbar-links" :class="{ 'is-open': isMenuOpen }">
      <router-link to="/" @click="closeMenu">首頁</router-link>
      <router-link to="/products" @click="closeMenu">商品</router-link>
      <router-link to="/cart" class="cart-link" @click="closeMenu">
        🛒
        <transition name="pop">
          <span v-if="cartCount > 0" class="cart-badge" :key="cartCount">{{ cartCount }}</span>
        </transition>
      </router-link>
      
      <div v-if="user" class="user-section">
        <router-link to="/profile" class="user-name" @click="closeMenu">會員中心</router-link>
        <a href="#" @click.prevent="handleLogout" class="logout-button">登出</a>
      </div>
      <router-link v-else to="/login" @click="closeMenu">登入</router-link>
    </div>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../../store/auth';
import { useCartStore } from '../../store/cart';

const router = useRouter();
const authStore = useAuthStore();
const cartStore = useCartStore();
const { user } = storeToRefs(authStore);
const cartCount = computed(() => cartStore.totalItems);

const isMenuOpen = ref(false);
const isScrolled = ref(false);

const toggleMenu = () => {
  isMenuOpen.value = !isMenuOpen.value;
};

const closeMenu = () => {
  isMenuOpen.value = false;
};

const handleLogout = () => {
  authStore.logout();
  closeMenu();
  router.push('/');
};

const handleScroll = () => {
  isScrolled.value = window.scrollY > 20;
};

onMounted(() => {
  window.addEventListener('scroll', handleScroll);
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll);
});
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: $dark-grey;
  border-bottom: 2px solid $primary-color;
  position: sticky;
  top: 0;
  z-index: 100;
  transition: all 0.3s ease;

  &.scrolled {
    background-color: $glass-bg;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-bottom: 1px solid $glass-border;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
    padding: 0.8rem 2rem;
  }

  .navbar-brand {
    a {
      font-size: 1.5rem;
      font-weight: 800;
      color: $primary-color;
      text-decoration: none;
      letter-spacing: 1px;
      font-family: $font-family-heading;
      
      &:hover {
        color: $primary-light;
        text-shadow: 0 0 10px $primary-glow;
      }
    }
  }

  .hamburger {
    display: none;
    flex-direction: column;
    justify-content: space-around;
    width: 30px;
    height: 25px;
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 0;
    z-index: 101;

    .bar {
      width: 30px;
      height: 3px;
      background-color: $text-primary;
      border-radius: 10px;
      transition: all 0.3s linear;
      position: relative;
      transform-origin: 1px;
    }

    &.is-active .bar:nth-child(1) { transform: rotate(45deg); }
    &.is-active .bar:nth-child(2) { opacity: 0; }
    &.is-active .bar:nth-child(3) { transform: rotate(-45deg); }
  }

  .navbar-links {
    display: flex;
    align-items: center;

    a {
      color: $text-secondary;
      text-decoration: none;
      margin-left: 1.5rem;
      font-size: 1rem;
      padding: 0.5rem 1rem;
      border-radius: $border-radius;
      transition: $transition-base;
      font-weight: 500;

      &:hover {
        color: $text-primary;
        background-color: rgba(255, 255, 255, 0.1);
      }

      &.router-link-exact-active {
        color: $text-primary;
        font-weight: 600;
        background-color: $primary-color;
        box-shadow: 0 4px 10px $primary-glow;
      }
    }

    .cart-link {
      position: relative;
      font-size: 1.2rem;

      .cart-badge {
        position: absolute;
        top: -4px;
        right: -8px;
        background: #ff4444;
        color: #fff;
        font-size: 0.65rem;
        font-weight: bold;
        min-width: 18px;
        height: 18px;
        border-radius: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
        line-height: 1;
        box-shadow: 0 2px 5px rgba(255, 68, 68, 0.4);
      }
    }

    .user-section {
      display: flex;
      align-items: center;
      margin-left: 1.5rem;

      .user-name {
        color: $text-primary;
        margin-right: 0.5rem;
      }

      .logout-button {
        color: $text-secondary;
        cursor: pointer;
        margin-left: 0;
        &:hover {
          color: $primary-light;
        }
      }
    }
  }

  @media (max-width: 768px) {
    .hamburger {
      display: flex;
    }

    .navbar-links {
      position: fixed;
      top: 0;
      right: -100%;
      width: 70%;
      height: 100vh;
      background-color: rgba(26, 26, 26, 0.95);
      backdrop-filter: blur(10px);
      flex-direction: column;
      align-items: center;
      justify-content: center;
      transition: right 0.4s ease;
      z-index: 100;
      box-shadow: -5px 0 15px rgba(0, 0, 0, 0.5);

      &.is-open {
        right: 0;
      }

      a {
        margin: 1rem 0;
        font-size: 1.2rem;
        width: 80%;
        text-align: center;
      }

      .user-section {
        flex-direction: column;
        margin-left: 0;
        width: 100%;
        
        .user-name {
          margin-right: 0;
          margin-bottom: 1rem;
        }
      }
    }
  }
}

// Cart Badge Animation
.pop-enter-active {
  animation: pop-in 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.pop-leave-active {
  animation: pop-in 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) reverse;
}
@keyframes pop-in {
  0% { transform: scale(0); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}
</style>
