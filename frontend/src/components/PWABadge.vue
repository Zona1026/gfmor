<template>
  <div v-if="needRefresh" class="pwa-toast" role="alert">
    <div class="message">
      <span>有新版本可用，點擊重新整理以更新。</span>
    </div>
    <div class="buttons">
      <button @click="updateServiceWorker()">重新整理</button>
      <button @click="close">關閉</button>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount } from 'vue'
import { useRegisterSW } from 'virtual:pwa-register/vue'

const UPDATE_INTERVAL_MS = 5 * 60 * 1000
const UPDATE_THROTTLE_MS = 60 * 1000

let registration
let updateInterval
let lastUpdateAt = 0

const checkForUpdate = async () => {
  if (!registration || !navigator.onLine) return

  const now = Date.now()
  if (now - lastUpdateAt < UPDATE_THROTTLE_MS) return

  lastUpdateAt = now
  try {
    await registration.update()
  } catch (error) {
    console.warn('SW update check failed', error)
  }
}

const checkWhenVisible = () => {
  if (document.visibilityState === 'visible') checkForUpdate()
}

const {
  needRefresh,
  updateServiceWorker,
} = useRegisterSW({
  onNeedReload() {
    window.location.reload()
  },
  onRegisteredSW(_swUrl, currentRegistration) {
    registration = currentRegistration
    checkForUpdate()

    if (!registration) return
    updateInterval = window.setInterval(checkForUpdate, UPDATE_INTERVAL_MS)
    window.addEventListener('focus', checkForUpdate)
    window.addEventListener('online', checkForUpdate)
    document.addEventListener('visibilitychange', checkWhenVisible)
  },
  onRegisterError(error) {
    console.warn('SW registration error', error)
  },
})

const close = () => {
  needRefresh.value = false
}

onBeforeUnmount(() => {
  if (updateInterval) window.clearInterval(updateInterval)
  window.removeEventListener('focus', checkForUpdate)
  window.removeEventListener('online', checkForUpdate)
  document.removeEventListener('visibilitychange', checkWhenVisible)
})
</script>

<style scoped>
.pwa-toast {
  position: fixed;
  right: 0;
  bottom: 0;
  margin: 16px;
  padding: 12px;
  border: 1px solid #8885;
  border-radius: 4px;
  z-index: 10000;
  text-align: left;
  box-shadow: 3px 4px 5px 0px #8885;
  background-color: #2c2c2c;
  color: #fff;
}
.pwa-toast .message {
  margin-bottom: 8px;
}
.pwa-toast .buttons {
  display: flex;
  gap: 8px;
}
.pwa-toast button {
  border: 1px solid #8885;
  outline: none;
  margin-right: 5px;
  border-radius: 2px;
  padding: 3px 10px;
  background-color: transparent;
  color: #fff;
  cursor: pointer;
}
</style>
