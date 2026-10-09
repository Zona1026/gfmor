<template>
  <fieldset>
    <legend>{{ title }}</legend>
    <div class="picker">
      <label>分類<select v-model="picker.category" @change="changeCategory"><option value="">全部分類</option><option v-for="category in categories" :key="category.value" :value="category.value">{{ category.name }}</option></select></label>
      <label>進貨廠商<select v-model="picker.supplier" @change="picker.productId = ''"><option value="">全部廠商</option><option v-for="supplier in suppliers" :key="supplier" :value="supplier">{{ supplier }}</option></select></label>
      <label>商品<select v-model="picker.productId"><option value="">請選擇商品</option><option v-for="product in filtered" :key="product.id" :value="String(product.id)" :disabled="modelValue.includes(product.id)">{{ product.name }}{{ product.model_number ? `（${product.model_number}）` : '' }}{{ modelValue.includes(product.id) ? '（已加入）' : '' }}</option></select></label>
    </div>
    <p v-if="!filtered.length">沒有符合此分類與廠商的商品。</p>
    <button type="button" :disabled="!canAdd || disabled" @click="add">{{ multiple ? '＋ 加入商品' : '設定贈品' }}</button>
    <p>已選 {{ modelValue.length }} 件商品</p>
    <div class="selected-list">
      <div v-for="product in selected" :key="product.id" class="selected"><span>{{ product.name }}{{ product.model_number ? `（${product.model_number}）` : '' }}</span><button type="button" :aria-label="`移除 ${product.name}`" :disabled="disabled" @click="$emit('update:modelValue', modelValue.filter(id => id !== product.id))">移除</button></div>
    </div>
  </fieldset>
</template>
<script setup>
import { computed, reactive } from 'vue';
import { categoryOptions, supplierOptions, filterPickerProducts } from '../../utils/workOrderProductPicker';
const props = defineProps({ modelValue: { type: Array, default: () => [] }, products: { type: Array, required: true }, fallback: { type: Array, default: () => [] }, title: { type: String, default: '適用商品（可複選）' }, multiple: { type: Boolean, default: true }, disabled: Boolean });
const emit = defineEmits(['update:modelValue']);
const picker = reactive({ category: '', supplier: '', productId: '' });
const categories = computed(() => categoryOptions(props.products));
const suppliers = computed(() => supplierOptions(props.products, picker.category));
const filtered = computed(() => filterPickerProducts(props.products, picker.category, picker.supplier));
const selected = computed(() => props.modelValue.map(id => props.products.find(product => product.id === id) || props.fallback.find(product => product.id === id) || { id, name: `商品 #${id}` }));
const canAdd = computed(() => filtered.value.some(product => product.id === Number(picker.productId)) && !props.modelValue.includes(Number(picker.productId)));
function changeCategory() { picker.supplier = ''; picker.productId = ''; }
function add() { if (!canAdd.value) return; emit('update:modelValue', props.multiple ? [...props.modelValue, Number(picker.productId)] : [Number(picker.productId)]); picker.productId = ''; }
</script>
<style scoped>
fieldset { min-width: 0; border: 1px solid #555; border-radius: 6px; padding: .8rem; }
.picker { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .65rem; margin-bottom: .8rem; }
label { display: grid; gap: .4rem; } select { min-width: 0; width: 100%; box-sizing: border-box; background: #111; color: #eee; padding: .65rem; border: 1px solid #444; border-radius: 6px; }
button { padding: .65rem .9rem; border: 1px solid #444; border-radius: 8px; background: #222; color: #eee; font: inherit; cursor: pointer; } button:disabled { opacity: .5; cursor: default; }
.selected-list { display: grid; gap: .65rem; max-height: 180px; overflow-y: auto; }
.selected { display: flex; justify-content: space-between; align-items: center; gap: .65rem; } span { overflow-wrap: anywhere; }
@media (max-width: 600px) { .picker { grid-template-columns: 1fr; } }
</style>
