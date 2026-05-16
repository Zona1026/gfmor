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
import { useRegisterSW } from 'virtual:pwa-register/vue'

const {
  needRefresh,
  updateServiceWorker,
} = useRegisterSW({
  onRegistered(r) {
    console.log('SW Registered: ', r)
  },
  onRegisterError(error) {
    console.log('SW registration error', error)
  },
})

const close = () => {
  needRefresh.value = false
}
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
