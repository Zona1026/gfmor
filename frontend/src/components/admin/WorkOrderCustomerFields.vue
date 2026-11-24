<template>
  <div class="customer-fields">
    <label>客人姓名<input v-model.trim="name" aria-label="工單客人姓名" :maxlength="workOrder.google_id || workOrder.booking?.user ? 10 : 50" :disabled="disabled || saving || !!workOrder.deleted_at" /></label>
    <label>客人電話<input v-model.trim="phone" aria-label="工單客人電話" type="tel" :maxlength="workOrder.google_id || workOrder.booking?.user ? 10 : 20" :disabled="disabled || saving || !!workOrder.deleted_at" /></label>
    <button v-if="!disabled && !workOrder.deleted_at" type="button" :disabled="saving || !changed" @click="save">{{ saving ? '儲存中…' : '儲存客人資訊' }}</button>
    <slot />
    <small v-if="error" role="alert">{{ error }}</small>
    <small v-else-if="message" role="status">{{ message }}</small>
  </div>
</template>
<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import { updateWorkOrderCustomer } from '../../api/admin';
const props = defineProps({ workOrder: { type: Object, required: true }, disabled: Boolean });
const emit = defineEmits(['saved']);
const name = ref(''), phone = ref(''), saving = ref(false), error = ref(''), message = ref('');
let requestId = 0;
watch(() => [props.workOrder.id, props.workOrder.customer_name, props.workOrder.customer_phone], () => {
  requestId++;
  name.value = props.workOrder.customer_name || '';
  phone.value = props.workOrder.customer_phone || '';
  saving.value = false;
  error.value = '';
  message.value = '';
}, { immediate: true });
const changed = computed(() => name.value !== (props.workOrder.customer_name || '') || phone.value !== (props.workOrder.customer_phone || ''));
async function save() {
  if (props.disabled || props.workOrder.deleted_at || saving.value || !changed.value) return;
  const id = props.workOrder.id;
  const currentRequest = ++requestId;
  saving.value = true;
  error.value = '';
  message.value = '';
  try {
    const saved = await updateWorkOrderCustomer(id, { name: name.value, phone: phone.value });
    if (currentRequest !== requestId || props.workOrder.id !== id) return;
    emit('saved', saved);
    await nextTick();
    if (props.workOrder.id === id) message.value = '客人資訊已儲存。';
  } catch (e) {
    if (currentRequest === requestId && props.workOrder.id === id) error.value = e.response?.data?.detail || '儲存客人資訊失敗，請重試。';
  } finally {
    if (currentRequest === requestId) saving.value = false;
  }
}
</script>
<style scoped>
.customer-fields { display: flex; align-items: end; flex-wrap: wrap; gap: .5rem; min-width: 0; width: 100%; }
label { display: grid; gap: .35rem; color: var(--admin-muted, #bdbdbd); font-size: .88rem; }
input { width: 160px; height: 40px; max-width: 100%; min-width: 0; box-sizing: border-box; padding: .5rem; border: 1px solid var(--admin-border, #424242); border-radius: 8px; background: var(--admin-surface, #212121); color: var(--admin-text, #eee); font: inherit; }
input:focus { outline: 2px solid var(--admin-accent, #ef5350); outline-offset: 1px; }
input:disabled { opacity: .65; }
button { height: 40px; box-sizing: border-box; padding: .5rem; border: 1px solid var(--admin-danger, #ef5350); border-radius: 6px; background: transparent; color: var(--admin-danger, #ef5350); cursor: pointer; }
button:disabled { opacity: .5; cursor: default; }
small { flex-basis: 100%; color: var(--admin-muted, #bdbdbd); }
[role=alert] { color: var(--admin-danger, #ffb4ab); }
</style>
