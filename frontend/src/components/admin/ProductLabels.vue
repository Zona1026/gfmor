<template>
  <section class="product-label-previews">
    <div class="label-heading">
      <strong>商品標籤預覽</strong>
      <button type="button" :disabled="!canPrint || contentOverflow" @click="printLabels">列印兩張標籤</button>
    </div>
    <p class="label-note">每個商品兩張，每張 3.6 × 2.5 公分。列印時使用 100% 比例，關閉頁首頁尾。</p>
    <div ref="labelPair" class="label-pair">
      <div class="label-preview-item">
        <span class="label-caption">資訊標籤</span>
        <article class="gf-product-label" :style="{ '--label-font-size': `${fontSize}pt` }">
          <div ref="infoBody" class="gf-label-info-body">
            <div class="gf-label-name">{{ form.name || '品項名稱' }}</div>
            <div v-if="vehicleModels" class="gf-label-detail">{{ vehicleModels }}</div>
            <div v-if="details" class="gf-label-detail">{{ details }}</div>
          </div>
          <div class="gf-label-price">
            <div>售價 NT$ {{ money(form.price) }}</div>
            <div>安裝工資 {{ laborQuote }}</div>
          </div>
        </article>
      </div>
      <div class="label-preview-item">
        <span class="label-caption">條碼標籤</span>
        <article class="gf-product-label gf-label-barcode">
          <template v-if="canPrint">
            <ProductBarcode :value="form.barcode" compact />
            <div class="gf-label-code">{{ form.barcode }}</div>
          </template>
          <span v-else class="barcode-placeholder">{{ form.barcode ? '條碼格式不正確' : '請填寫商品條碼' }}</span>
        </article>
      </div>
    </div>
    <p v-if="contentOverflow" class="label-error" role="alert">資訊超出標籤範圍，請縮短商品名稱或規格後再列印。</p>
    <p v-if="printError" class="label-error" role="alert">{{ printError }}</p>
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import ProductBarcode from './ProductBarcode.vue';
import labelStyles from '../../assets/productLabels.css?inline';
const props = defineProps({ form: { type: Object, required: true } });
const labelPair = ref(null);
const infoBody = ref(null);
const fontSize = ref(7);
const contentOverflow = ref(false);
const printError = ref('');
const money = value => Number(value || 0).toLocaleString('zh-TW');
const vehicleModels = computed(() => (props.form.vehicle_models || []).join('、'));
const details = computed(() => [props.form.model_number, props.form.specification, props.form.color].filter(Boolean).join(' ／ '));
const laborQuote = computed(() => props.form.installation_labor === '' || props.form.installation_labor == null
  ? '未設定' : Number(props.form.installation_labor) === 0 ? '免工資' : `NT$ ${money(props.form.installation_labor)}`);
const canPrint = computed(() => /^[!-~]{1,100}$/.test(props.form.barcode || ''));
let fitRequestId = 0;
watch(() => [props.form.name, vehicleModels.value, details.value, props.form.price, laborQuote.value], async () => {
  const requestId = ++fitRequestId;
  fontSize.value = 7;
  contentOverflow.value = false;
  await nextTick();
  while (requestId === fitRequestId && infoBody.value && infoBody.value.scrollHeight > infoBody.value.clientHeight + 1 && fontSize.value > 5.5) {
    fontSize.value -= 0.5;
    await nextTick();
  }
  if (requestId === fitRequestId && infoBody.value) contentOverflow.value = infoBody.value.scrollHeight > infoBody.value.clientHeight + 1;
}, { immediate: true });
function printLabels() {
  if (!canPrint.value || contentOverflow.value || !labelPair.value) return;
  printError.value = '';
  const popup = window.open('', '_blank', 'width=480,height=420');
  if (!popup) { printError.value = '請允許此網站開啟列印視窗。'; return; }
  popup.document.title = '商品標籤 — 36 × 25 mm';
  const style = popup.document.createElement('style');
  style.textContent = `${labelStyles}
    @page { size:36mm 25mm; margin:0; }
    html, body { margin:0; padding:0; width:36mm; background:white; }
    .gf-product-label { break-after:page; page-break-after:always; print-color-adjust:exact; }
    .gf-product-label:last-child { break-after:auto; page-break-after:auto; }`;
  popup.document.head.appendChild(style);
  for (const label of labelPair.value.querySelectorAll('.gf-product-label')) popup.document.body.appendChild(label.cloneNode(true));
  popup.addEventListener('afterprint', () => popup.close(), { once:true });
  popup.requestAnimationFrame(() => { popup.focus(); popup.print(); });
}
</script>
<style src="../../assets/productLabels.css"></style>
<style lang="scss" scoped>
@import '../../assets/_variables.scss';
.product-label-previews { padding:0.85rem; border:1px dashed $medium-grey; border-radius:$border-radius; background:$background-color; }
.label-heading { display:flex; align-items:center; justify-content:space-between; gap:0.5rem; flex-wrap:wrap; }
.label-heading strong { color:$primary-light; }
.label-heading button { border:1px solid $medium-grey; border-radius:$border-radius; background:transparent; color:$text-primary; padding:0.45rem 0.7rem; cursor:pointer; }
.label-heading button:disabled { opacity:0.5; cursor:not-allowed; }
.label-note, .label-caption { font-size:0.8rem; color:$text-secondary; }
.label-pair { display:flex; gap:1rem; flex-wrap:wrap; }
.label-caption { display:block; margin-bottom:0.4rem; }
.barcode-placeholder { font-size:7pt; }
.label-error { color:#ffb74d; font-size:0.85rem; margin-bottom:0; }
</style>
