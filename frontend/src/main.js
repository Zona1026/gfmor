import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/main.scss'
import vue3GoogleLogin from 'vue3-google-login'

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
app.mount('#app')
