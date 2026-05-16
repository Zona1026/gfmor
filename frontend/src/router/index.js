import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import ProfileComplete from '../views/ProfileComplete.vue'
import MemberCenter from '../views/MemberCenter.vue'
import Products from '../views/Products.vue'
import Cart from '../views/Cart.vue'
import Checkout from '../views/Checkout.vue'
import PortfolioCategory from '../views/PortfolioCategory.vue'
import ProjectDetail from '../views/ProjectDetail.vue'
import Booking from '../views/Booking.vue'
import PrivacyPolicy from '../views/PrivacyPolicy.vue'
import TermsOfService from '../views/TermsOfService.vue'
import AdminDashboard from '../views/admin/Dashboard.vue'
import AdminBookings from '../views/admin/Bookings.vue'
import AdminMembers from '../views/admin/Members.vue'
import AdminAnnouncements from '../views/admin/Announcements.vue'
import AdminPortfolio from '../views/admin/Portfolio.vue'
import AdminProducts from '../views/admin/Products.vue'
import AdminOrders from '../views/admin/Orders.vue'
import AdminAdmins from '../views/admin/Admins.vue'
import { useAuthStore } from '../store/auth'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/profile/complete',
    name: 'ProfileComplete',
    component: ProfileComplete,
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'MemberCenter',
    component: MemberCenter,
    meta: { requiresAuth: true }
  },
  {
    path: '/booking',
    name: 'Booking',
    component: Booking,
    meta: { requiresAuth: true }
  },
  {
    path: '/cart',
    name: 'Cart',
    component: Cart
  },
  {
    path: '/checkout',
    name: 'Checkout',
    component: Checkout,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: AdminDashboard,
    meta: { requiresAdmin: true },
    children: [
      {
        path: 'bookings',
        name: 'AdminBookings',
        component: AdminBookings
      },
      {
        path: 'members',
        name: 'AdminMembers',
        component: AdminMembers
      },
      {
        path: 'announcements',
        name: 'AdminAnnouncements',
        component: AdminAnnouncements
      },
      {
        path: 'portfolio',
        name: 'AdminPortfolio',
        component: AdminPortfolio
      },
      {
        path: 'products',
        name: 'AdminProducts',
        component: AdminProducts
      },
      {
        path: 'orders',
        name: 'AdminOrders',
        component: AdminOrders
      },
      {
        path: 'admins',
        name: 'AdminAdmins',
        component: AdminAdmins
      }
    ]
  },
  {
    path: '/products',
    name: 'Products',
    component: Products
  },
  {
    path: '/portfolio/:category',
    name: 'PortfolioCategory',
    component: PortfolioCategory,
    props: true
  },
  {
    path: '/portfolio/project/:id',
    name: 'ProjectDetail',
    component: ProjectDetail,
    props: true
  },
  {
    path: '/privacy',
    name: 'PrivacyPolicy',
    component: PrivacyPolicy
  },
  {
    path: '/terms',
    name: 'TermsOfService',
    component: TermsOfService
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全域導航守衛
router.beforeEach((to, from) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAdmin && !authStore.adminToken) {
    return '/login'
  }

  if (to.meta.requiresAuth && !authStore.user) {
    return '/login'
  }

  if (authStore.user) {
    const isProfileIncomplete = !authStore.user.phone || !authStore.user.motors || authStore.user.motors.length === 0;
    
    if (isProfileIncomplete && to.path !== '/profile/complete' && to.path !== '/login') {
      return '/profile/complete'
    }
  }
  
  return true
})

export default router
