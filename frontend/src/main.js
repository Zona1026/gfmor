import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/main.scss'
import vue3GoogleLogin from 'vue3-google-login'
import { ADMIN_IDLE_TIMEOUT_HOURS, useAuthStore } from './store/auth'

const app = createApp(App)

app.config.errorHandler = (err, instance, info) => {
  console.error("Vue Global Error:", err, info);
  const div = document.createElement('div');
  div.style.cssText = 'position:fixed;top:0;left:0;right:0;background:red;color:white;padding:20px;z-index:999999;font-size:16px;white-space:pre-wrap;';
  div.innerText = 'FATAL EXCEPTION:\n' + err.stack + '\nInfo: ' + info;
  document.body.appendChild(div);
};

window.addEventListener('error', (event) => {
  const div = document.createElement('div');
  div.style.cssText = 'position:fixed;bottom:0;left:0;right:0;background:darkred;color:white;padding:20px;z-index:999999;font-size:16px;white-space:pre-wrap;';
  div.innerText = 'WINDOW ERROR:\n' + event.error?.stack;
  document.body.appendChild(div);
});

app.use(createPinia())
app.use(router)
app.use(vue3GoogleLogin, {
  clientId: '357528958616-1mbtrri5ii7irbqpftd8ml3qtdr7ho0u.apps.googleusercontent.com'
})

const ADMIN_ACTIVITY_WRITE_INTERVAL_MS = 15 * 1000
const ADMIN_ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'input', 'scroll', 'touchstart']

let lastAdminActivityWriteAt = 0
let isHandlingAdminTimeout = false

const handleAdminActivity = (event) => {
  const authStore = useAuthStore();
  if (!authStore.adminToken) return;

  if (authStore.isAdminSessionIdle()) {
    if (isHandlingAdminTimeout) return;
    isHandlingAdminTimeout = true;
    authStore.adminLogout();
    if (event?.cancelable) event.preventDefault();
    event?.stopPropagation?.();
    alert(`閒置超過 ${ADMIN_IDLE_TIMEOUT_HOURS} 小時，請重新登入。`);
    router.push('/admin-login');
    return;
  }

  const now = Date.now();
  if (now - lastAdminActivityWriteAt >= ADMIN_ACTIVITY_WRITE_INTERVAL_MS) {
    authStore.setAdminActivity(now);
    lastAdminActivityWriteAt = now;
  }
};

ADMIN_ACTIVITY_EVENTS.forEach((eventName) => {
  window.addEventListener(eventName, handleAdminActivity, {
    capture: true,
    passive: eventName === 'scroll',
  });
});

window.addEventListener('focus', handleAdminActivity);
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') handleAdminActivity();
});

app.mount('#app')
