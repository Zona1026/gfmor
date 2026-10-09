<template>
  <div class="barcode-preview">
    <svg v-show="!error" ref="barcodeElement" role="img" :aria-label="`商品條碼 ${value}`" />
    <span v-if="error" role="alert">{{ error }}</span>
  </div>
</template>
<script setup>
import { nextTick, ref, watch } from 'vue';
import JsBarcode from 'jsbarcode';
const props = defineProps({ value: { type: String, required: true } });
const barcodeElement = ref(null);
const error = ref('');
watch(() => props.value, async value => {
  await nextTick();
  error.value = '';
  if (!barcodeElement.value) return;
  try {
    if (!/^[!-~]{1,100}$/.test(value)) throw new Error();
    JsBarcode(barcodeElement.value, value, { format: 'CODE128', width: 2, height: 52, fontSize: 14, margin: 12, background: '#ffffff', lineColor: '#000000' });
    barcodeElement.value.setAttribute('viewBox', `0 0 ${parseFloat(barcodeElement.value.getAttribute('width'))} ${parseFloat(barcodeElement.value.getAttribute('height'))}`);
  } catch {
    error.value = '條碼限 100 字以內的英數字或符號，不可包含空白。';
  }
}, { immediate: true });
</script>
<style scoped>
.barcode-preview { margin-top: 0.6rem; max-width: 100%; overflow-x: auto; }
svg { display: block; max-width: 100%; height: auto; }
span { color: #ffb74d; }
</style>
