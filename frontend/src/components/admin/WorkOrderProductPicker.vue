<template>
  <div class="product-picker" :class="{ 'labor-picker': ['LABOR', 'MAJOR_MAINTENANCE'].includes(item.type) }">
    <label class="picker-type">
      <span>類型</span>
      <select v-model="item.type" :disabled="disabled" @change="changeType">
        <option v-for="(label, value) in types" :key="value" :value="value">{{ label }}</option>
      </select>
    </label>
    <label class="picker-category" v-if="!['LABOR', 'MAJOR_MAINTENANCE'].includes(item.type)">
      <span>零件分類</span>
      <select v-model="item.picker_category" :disabled="disabled || !['PART', 'LABOR'].includes(item.type)" @change="changeCategory">
        <option value="">{{ ['PART', 'LABOR'].includes(item.type) ? '全部分類' : '不適用' }}</option>
        <option v-if="item.type === 'PART'" :value="MANUAL_PRODUCT_CATEGORY">不綁商品 / 不扣庫存</option>
        <option v-for="category in categories" :key="category.value" :value="category.value">{{ category.name }}</option>
      </select>
    </label>
    <label class="picker-manufacturer">
      <span>廠商</span>
      <select v-model="item.picker_manufacturer" :disabled="disabled || item.type !== 'PART' || isManual" @change="changeFilters">
        <option value="">{{ item.type === 'PART' && !isManual ? '全部廠商' : '不適用' }}</option>
        <option v-for="name in manufacturers" :key="name" :value="name">{{ name }}</option>
      </select>
    </label>
    <div class="product-field">
      <span>商品名稱</span>
      <WorkOrderProductSelect v-if="['PART', 'LABOR', 'MAJOR_MAINTENANCE'].includes(item.type) && !isManual"
        :products="matchingProducts" :model-value="item.product_id" :fallback-label="item.name" :disabled="disabled"
        @select="selectProduct" />
      <input v-else-if="isManual" v-model.trim="item.name" aria-label="商品名稱" :disabled="disabled" placeholder="請輸入商品名稱" required />
      <input v-else value="不適用" disabled />
    </div>
  </div>
</template>
<script setup>
import { computed, watch } from 'vue';
import WorkOrderProductSelect from './WorkOrderProductSelect.vue';
import { categoryOptions, manufacturerOptions, filterWorkOrderProducts, MANUAL_PRODUCT_CATEGORY } from '../../utils/workOrderProductPicker';
const props = defineProps({
  item: { type: Object, required: true }, products: { type: Array, required: true },
  types: { type: Object, required: true }, disabled: { type: Boolean, default: false }
});
const emit = defineEmits(['select-product', 'change-type']);
watch(() => props.item, item => {
  item.picker_category ??= item.type === 'PART' && !item.product_id ? MANUAL_PRODUCT_CATEGORY : '';
  item.picker_manufacturer ??= '';
}, { immediate: true });
const isManual = computed(() => props.item.type === 'PART' && props.item.picker_category === MANUAL_PRODUCT_CATEGORY);
const parts = computed(() => props.products.filter(product => (['LABOR', 'MAJOR_MAINTENANCE'].includes(props.item.type)
  ? product.inventory_type === props.item.type
  : ['PART', 'BOTH'].includes(product.inventory_type))
  || product.id === Number(props.item.product_id)));
const categories = computed(() => categoryOptions(parts.value, { selectedValue: props.item.picker_category }));
const manufacturers = computed(() => manufacturerOptions(parts.value, props.item.picker_category));
const matchingProducts = computed(() => ['LABOR', 'MAJOR_MAINTENANCE'].includes(props.item.type)
  ? parts.value
  : filterWorkOrderProducts(parts.value, props.item.picker_category, props.item.picker_manufacturer));
function changeFilters() {
  if (props.item.product_id && !matchingProducts.value.some(product => product.id === Number(props.item.product_id))) {
    props.item.product_id = null;
    props.item.name = '';
    props.item.unit_price = 0;
  }
}
function selectProduct(id) {
  props.item.product_id = id;
  emit('select-product', props.item);
}
function changeCategory() {
  if (isManual.value || !props.item.product_id) {
    props.item.product_id = null;
    props.item.name = '';
    props.item.unit_price = 0;
    props.item.promotion_name = '';
    delete props.item.promotion_auto_price;
  }
  if (!manufacturers.value.includes(props.item.picker_manufacturer)) props.item.picker_manufacturer = '';
  changeFilters();
}
function changeType() {
  props.item.picker_category = '';
  props.item.picker_manufacturer = '';
  props.item.product_id = null;
  emit('change-type', props.item);
}
</script>
<style scoped>
.product-picker { display: grid; grid-template-columns: minmax(90px, 0.6fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.6fr); gap: 0.5rem; min-width: 0; }
.labor-picker { grid-template-columns: minmax(90px, 0.6fr) minmax(0, 1fr) minmax(0, 1.6fr); }
label, .product-field { display: grid; gap: 0.28rem; min-width: 0; }
span { font-size: 0.78rem; font-weight: 700; color: var(--admin-text, #ddd); }
input, select { width: 100%; min-width: 0; height: 38px; box-sizing: border-box; border: 1px solid var(--admin-border, #444); border-radius: 6px; background: var(--admin-surface, #202124); color: var(--admin-text, #eee); padding: 0.45rem 0.65rem; }
select:disabled, input:disabled { opacity: 0.6; }
.picker-quote { grid-column: 1 / -1; font-size: 0.78rem; line-height: 1.5; overflow-wrap: anywhere; color: var(--admin-text, #ddd); }
@media (max-width: 700px) { .product-picker, .labor-picker { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 420px) { .product-picker, .labor-picker { grid-template-columns: minmax(0, 1fr); } }
</style>
