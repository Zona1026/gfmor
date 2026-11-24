<template>
  <div class="vehicle-brand-fields" :aria-busy="loading">
    <label>廠牌
      <select :value="brand || ''" :disabled="disabled" @change="$emit('update:brand', $event.target.value)">
        <option value="">未填寫</option>
        <option v-for="value in brandOptions" :key="value" :value="value">{{ value }}</option>
      </select>
    </label>
    <span class="separator" aria-hidden="true">－</span>
    <label>廠牌型式
      <select :value="brandType || ''" :disabled="disabled" @change="$emit('update:brandType', $event.target.value)">
        <option value="">未填寫</option>
        <option v-for="value in brandTypeOptions" :key="value" :value="value">{{ value }}</option>
      </select>
    </label>
    <small v-if="error" role="alert">{{ error }} <button type="button" :disabled="loading" @click="load">重試</button></small>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue';
import { getVehicleBrandOptions } from '../../api/admin';
import { vehicleBrandOptions } from '../../utils/vehicleBrandOptions';
const props = defineProps({ brand: String, brandType: String, disabled: Boolean });
defineEmits(['update:brand', 'update:brandType']);
const options = ref({ brands: [], brand_types: [] });
const loading = ref(false), error = ref('');
const brandOptions = computed(() => vehicleBrandOptions(options.value.brands, props.brand));
const brandTypeOptions = computed(() => vehicleBrandOptions(options.value.brand_types, props.brandType));
async function load() {
  loading.value = true;
  error.value = '';
  try { options.value = await getVehicleBrandOptions(); }
  catch { error.value = '廠牌選單載入失敗，請重試。'; }
  finally { loading.value = false; }
}
onMounted(load);
</script>
<style scoped>
.vehicle-brand-fields { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); gap: .3rem; min-width: 0; }
label { display: flex; flex-direction: column; gap: .5rem; min-width: 0; color: var(--admin-muted, #bdbdbd); font-size: .88rem; }
select { width: 100%; min-width: 0; box-sizing: border-box; padding: .65rem .35rem; border: 1px solid var(--admin-border, #424242); border-radius: 8px; background: var(--admin-surface, #212121); color: var(--admin-text, #eee); font: inherit; }
select:focus { outline: 2px solid var(--admin-accent, #ef5350); outline-offset: 1px; }
select:disabled { opacity: .65; }
.separator { align-self: end; padding-bottom: .7rem; color: var(--admin-muted, #bdbdbd); }
small { grid-column: 1 / -1; color: var(--admin-danger, #ffb4ab); }
button { cursor: pointer; border: 1px solid var(--admin-danger, #ef5350); border-radius: 6px; background: transparent; color: var(--admin-danger, #ef5350); }
</style>
