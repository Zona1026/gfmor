<template>
  <div class="product-picker">
    <label>
      <span>類型</span>
      <select v-model="item.type" :disabled="disabled" @change="changeType">
        <option v-for="(label, value) in types" :key="value" :value="value">{{ label }}</option>
      </select>
    </label>
    <label>
      <span>分類</span>
      <select v-model="item.picker_category" :disabled="disabled || item.type !== 'PART'" @change="changeCategory">
        <option value="">{{ item.type === 'PART' ? '全部分類' : '不適用' }}</option>
        <option v-if="item.type === 'PART'" :value="MANUAL_PRODUCT_CATEGORY">不綁商品 / 不扣庫存</option>
        <option v-for="category in categories" :key="category.value" :value="category.value">{{ category.name }}</option>
      </select>
    </label>
    <label>
      <span>廠商</span>
      <select v-model="item.picker_supplier" :disabled="disabled || item.type !== 'PART' || isManual" @change="changeFilters">
        <option value="">{{ item.type === 'PART' && !isManual ? '全部廠商' : '不適用' }}</option>
        <option v-for="name in suppliers" :key="name" :value="name">{{ name }}</option>
      </select>
    </label>
    <label>
      <span>商品名稱</span>
      <select v-if="item.type === 'PART' && !isManual" v-model.number="item.product_id" :disabled="disabled" @change="$emit('select-product', item)">
        <option :value="null" disabled>請選擇商品</option>
        <option v-for="product in matchingProducts" :key="product.id" :value="product.id">{{ product.name }}{{ product.model_number ? `（${product.model_number}）` : '' }}</option>
      </select>
      <input v-else-if="isManual" v-model.trim="item.name" :disabled="disabled" placeholder="請輸入商品名稱" required />
      <input v-else value="不適用" disabled />
    </label>
  </div>
</template>
<script setup>
import { computed, watch } from 'vue';
import { categoryOptions, supplierOptions, filterPickerProducts, MANUAL_PRODUCT_CATEGORY } from '../../utils/workOrderProductPicker';
const props = defineProps({
  item: { type: Object, required: true }, products: { type: Array, required: true },
  types: { type: Object, required: true }, disabled: { type: Boolean, default: false }
});
const emit = defineEmits(['select-product', 'change-type']);
watch(() => props.item, item => {
  item.picker_category ??= item.type === 'PART' && !item.product_id ? MANUAL_PRODUCT_CATEGORY : '';
  item.picker_supplier ??= '';
}, { immediate: true });
const isManual = computed(() => props.item.type === 'PART' && props.item.picker_category === MANUAL_PRODUCT_CATEGORY);
const parts = computed(() => props.products.filter(product => product.inventory_type !== 'SHOP'
  || product.id === Number(props.item.product_id)));
const categories = computed(() => categoryOptions(parts.value));
const suppliers = computed(() => supplierOptions(parts.value, props.item.picker_category));
const matchingProducts = computed(() => filterPickerProducts(parts.value, props.item.picker_category, props.item.picker_supplier));
function changeFilters() {
  if (props.item.product_id && !matchingProducts.value.some(product => product.id === Number(props.item.product_id))) {
    props.item.product_id = null;
    props.item.name = '';
    props.item.unit_price = 0;
  }
}
function changeCategory() {
  if (isManual.value || !props.item.product_id) {
    props.item.product_id = null;
    props.item.name = '';
    props.item.unit_price = 0;
    props.item.promotion_name = '';
    delete props.item.promotion_auto_price;
  }
  if (!suppliers.value.includes(props.item.picker_supplier)) props.item.picker_supplier = '';
  changeFilters();
}
function changeType() {
  props.item.picker_category = '';
  props.item.picker_supplier = '';
  emit('change-type', props.item);
}
</script>
<style scoped>
.product-picker { display: grid; grid-template-columns: minmax(90px, 0.6fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.6fr); gap: 0.5rem; min-width: 0; }
label { display: grid; gap: 0.28rem; min-width: 0; }
span { font-size: 0.78rem; font-weight: 700; color: #ddd; }
input, select { width: 100%; min-width: 0; height: 38px; box-sizing: border-box; border: 1px solid #444; border-radius: 6px; background: #202124; color: #eee; padding: 0.45rem 0.65rem; }
select:disabled, input:disabled { opacity: 0.6; }
.picker-quote { grid-column: 1 / -1; font-size: 0.78rem; line-height: 1.5; overflow-wrap: anywhere; color: #ddd; }
@media (max-width: 700px) { .product-picker { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 420px) { .product-picker { grid-template-columns: minmax(0, 1fr); } }
</style>
