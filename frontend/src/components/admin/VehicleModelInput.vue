<template>
  <div class="vehicle-model-input">
    <input :value="modelValue" :list="listId" :disabled="disabled" :required="required" maxlength="200"
      placeholder="選擇或輸入車種" @input="$emit('update:modelValue', $event.target.value)" />
    <datalist :id="listId"><option v-for="name in options" :key="name" :value="name" /></datalist>
    <button v-if="!disabled && modelValue?.trim() && !options.includes(modelValue.trim())" type="button"
      :disabled="saving" @click="addOption">{{ saving ? '新增中…' : '新增為車種選項' }}</button>
    <small v-if="error" role="alert">{{ error }}</small>
  </div>
</template>
<script setup>
import { onMounted, ref, useId } from 'vue';
import { createProductVehicleModel, getProductVehicleModels } from '../../api/admin';
const props = defineProps({ modelValue: String, disabled: Boolean, required: Boolean });
const emit = defineEmits(['update:modelValue']);
const listId = useId();
const options = ref([]);
const saving = ref(false);
const error = ref('');
onMounted(async () => {
  try { options.value = await getProductVehicleModels(); }
  catch { error.value = '車種選單載入失敗，仍可自由填寫。'; }
});
async function addOption() {
  saving.value = true;
  error.value = '';
  try {
    const name = await createProductVehicleModel(props.modelValue.trim());
    options.value = [...new Set([...options.value, name])];
    emit('update:modelValue', name);
  } catch (e) { error.value = e.response?.data?.detail || '新增車種失敗，請稍後再試。'; }
  finally { saving.value = false; }
}
</script>
<style scoped>
.vehicle-model-input { display: grid; gap: .35rem; min-width: 0; }
input { width: 100%; min-width: 0; box-sizing: border-box; padding: .65rem .75rem; border: 1px solid var(--admin-border, #424242); border-radius: 8px; background: var(--admin-surface, #212121); color: var(--admin-text, #eee); font: inherit; }
input:focus { outline: 2px solid var(--admin-accent, #ef5350); outline-offset: 1px; }
input:disabled { opacity: .65; }
small { color: var(--admin-danger, #ffb4ab); }
button { cursor: pointer; padding: .45rem; border: 1px solid var(--admin-danger, #ef5350); border-radius: 6px; background: transparent; color: var(--admin-danger, #ef5350); }
</style>
