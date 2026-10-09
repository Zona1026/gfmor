<template>
  <section class="product-details-fields">
    <div class="details-grid">
      <label>車種
        <span class="vehicle-control">
          <select v-model="form.vehicle_model" :aria-busy="loadingModels">
            <option value="">未指定車種</option>
            <option v-for="name in vehicleModelOptions" :key="name" :value="name">{{ name }}</option>
          </select>
          <button type="button" @click="showNewModel = !showNewModel">＋ 新增車種</button>
        </span>
      </label>
      <label>商品條碼<input v-model.trim="form.barcode" type="text" maxlength="100" placeholder="可掃描或輸入商品條碼" autocomplete="off" @keydown.enter.prevent /></label>
      <label>型號<input v-model.trim="form.model_number" type="text" maxlength="200" placeholder="例如：產品型號、料號" /></label>
      <label>規格<input v-model.trim="form.specification" type="text" maxlength="500" placeholder="例如：尺寸、容量" /></label>
      <label>顏色<input v-model.trim="form.color" type="text" maxlength="100" /></label>
      <label>製造廠商<input v-model.trim="form.manufacturer" type="text" maxlength="200" /></label>
      <label>安裝工資（NT$）<input v-model.number="form.installation_labor" type="number" min="0" step="1" placeholder="未設定；0 表示免工資" /></label>
    </div>
    <div v-if="showNewModel" class="new-model-row">
      <label>新車種名稱<input v-model.trim="newModelName" type="text" maxlength="200" placeholder="例如：YAMAHA 勁戰六代" @keydown.enter.prevent="addVehicleModel" /></label>
      <button type="button" :disabled="savingModel || !newModelName" @click="addVehicleModel">{{ savingModel ? '新增中…' : '新增並選取' }}</button>
    </div>
    <p v-if="modelError" class="model-error" role="alert">{{ modelError }}</p>
    <div class="supplier-heading">
      <strong>進貨廠商、進價與同行價</strong>
      <button type="button" @click="form.supplier_prices.push({ supplier_name: '', purchase_price: '', wholesale_price: '' })">＋ 新增廠商</button>
    </div>
    <p class="field-note">每家廠商可設定不同同行價；未設定可留空，0 表示零元。空白列不會儲存，進價僅供管理層查看。</p>
    <div v-for="(supplier, index) in form.supplier_prices" :key="index" class="supplier-row">
      <label>進貨廠商 {{ index + 1 }}<input v-model.trim="supplier.supplier_name" type="text" maxlength="200" :required="supplier.purchase_price !== '' || supplier.wholesale_price !== ''" /></label>
      <label>進價（NT$）<input v-model.number="supplier.purchase_price" type="number" min="0" step="1" :required="!!supplier.supplier_name" /></label>
      <label>同行價（NT$）<input v-model.number="supplier.wholesale_price" type="number" min="0" step="1" placeholder="未設定" /></label>
      <button type="button" :aria-label="`移除進貨廠商 ${index + 1}`" @click="form.supplier_prices.splice(index, 1)">移除</button>
    </div>
    <div class="label-preview">
      <strong>標籤／報價資料預覽</strong>
      <div>{{ form.name || '品項名稱' }}</div>
      <div v-if="[form.vehicle_model, form.model_number, form.specification, form.color, form.manufacturer].some(Boolean)">{{ [form.vehicle_model, form.model_number, form.specification, form.color, form.manufacturer].filter(Boolean).join(' ／ ') }}</div>
      <div>建議售價 NT$ {{ money(form.price) }}</div>
      <div v-for="(supplier, index) in form.supplier_prices.filter(row => row.supplier_name)" :key="index">{{ supplier.supplier_name }} 同行價 {{ quote(supplier.wholesale_price) }}</div>
      <div v-if="form.legacy_wholesale_price !== ''">舊單一同行價 {{ quote(form.legacy_wholesale_price) }}（請確認後填入對應廠商）</div>
      <div>安裝工資 {{ quote(form.installation_labor) }}</div>
      <ProductBarcode v-if="form.barcode" :value="form.barcode" />
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import ProductBarcode from './ProductBarcode.vue';
import { createProductVehicleModel, getProductVehicleModels } from '../../api/admin';

const props = defineProps({ form: { type: Object, required: true } });
const vehicleModels = ref(['通用']);
const loadingModels = ref(false);
const showNewModel = ref(false);
const newModelName = ref('');
const savingModel = ref(false);
const modelError = ref('');
const vehicleModelOptions = computed(() => {
  const names = new Set([...vehicleModels.value, props.form.vehicle_model].filter(Boolean));
  return ['通用', ...[...names].filter(name => name !== '通用').sort((a, b) => a.localeCompare(b, 'zh-TW'))];
});

onMounted(async () => {
  loadingModels.value = true;
  try {
    vehicleModels.value = await getProductVehicleModels();
  } catch (error) {
    modelError.value = '車種清單載入失敗，請重新開啟表單；也可使用新增車種。';
  } finally {
    loadingModels.value = false;
  }
});

async function addVehicleModel() {
  const name = newModelName.value.trim();
  if (!name || savingModel.value) return;
  savingModel.value = true;
  modelError.value = '';
  try {
    const savedName = await createProductVehicleModel(name);
    vehicleModels.value = [...new Set([...vehicleModels.value, savedName])];
    props.form.vehicle_model = savedName;
    newModelName.value = '';
    showNewModel.value = false;
  } catch (error) {
    modelError.value = '新增車種失敗，請稍後再試。';
  } finally {
    savingModel.value = false;
  }
}
const money = value => Number(value || 0).toLocaleString('zh-TW');
const quote = value => value === '' || value === null || value === undefined ? '未設定' : `NT$ ${money(value)}`;
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';
.product-details-fields { display: flex; flex-direction: column; gap: 0.8rem; }
.details-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.8rem; }
label { display: flex; flex-direction: column; gap: 0.42rem; color: $text-secondary; font-size: 0.86rem; min-width: 0; }
input, select { width: 100%; min-height: 38px; padding: 0.52rem 0.72rem; box-sizing: border-box; background: $background-color; border: 1px solid $medium-grey; border-radius: $border-radius; color: $text-primary; font-size: 0.9rem; }
input:focus, select:focus { outline: none; border-color: $primary-color; }
.vehicle-control, .new-model-row { display: flex; gap: 0.5rem; align-items: end; }
.vehicle-control select, .new-model-row label { flex: 1; min-width: 0; }
.vehicle-control button, .new-model-row button { flex-shrink: 0; white-space: nowrap; }
.model-error { color: #ffb74d; font-size: 0.85rem; margin: 0; }
button { padding: 0.45rem 0.7rem; border: 1px solid $medium-grey; background: transparent; color: $text-secondary; border-radius: $border-radius; cursor: pointer; min-height: 38px; }
button:hover { border-color: $primary-color; color: $primary-light; }
.supplier-heading { display: flex; justify-content: space-between; align-items: center; gap: 0.7rem; }
.supplier-row { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr) minmax(0, 1fr) auto; gap: 0.65rem; align-items: end; }
.field-note { color: $text-secondary; margin: 0; font-size: 0.82rem; line-height: 1.6; }
.label-preview { background: $background-color; border: 1px dashed $medium-grey; border-radius: $border-radius; padding: 0.85rem; font-size: 0.85rem; line-height: 1.8; overflow-wrap: anywhere; }
.label-preview strong { display: block; color: $primary-light; margin-bottom: 0.3rem; }
@media (max-width: 600px) { .details-grid { grid-template-columns: 1fr; } .supplier-row { grid-template-columns: repeat(2, minmax(0, 1fr)); } .supplier-row label:first-child { grid-column: 1 / -1; } .supplier-row button { grid-column: 2; } }
</style>
