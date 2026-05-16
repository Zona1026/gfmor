<template>
  <div id="main-app">
    <Navbar v-if="!isAdminRoute" />
    <main class="main-content" :class="{ 'admin-layout': isAdminRoute }">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <Footer v-if="!isAdminRoute" />
    <PWABadge />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import Navbar from './components/layout/Navbar.vue';
import Footer from './components/layout/Footer.vue';
import PWABadge from './components/PWABadge.vue';

const route = useRoute();

const isAdminRoute = computed(() => {
  return route && route.path && route.path.startsWith('/admin');
});
</script>

<style lang="scss">
.main-content {
  padding: 1rem;
  
  &.admin-layout {
    padding: 0;
    height: 100vh;
  }
}
</style>
