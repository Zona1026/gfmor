<template>
  <div class="quick-overlay" v-backdrop-close="() => $emit('close')">
    <section class="quick-panel" role="dialog" aria-modal="true" aria-labelledby="quick-title" @keydown.esc.stop.prevent="$emit('close')">
      <header><div><span class="eyebrow">快速加入工單</span><h3 id="quick-title">商品快速點選</h3></div><button ref="closeButton" type="button" aria-label="關閉商品快速點選" @click="$emit('close')">×</button></header>
      <div class="quick-filters">
        <label class="quick-search"><span>搜尋商品</span><input ref="searchInput" v-model="query" placeholder="商品名稱、規格、顏色" type="search" /></label>
        <label><span>類型</span><select v-model="type" @change="category = ''; manufacturer = ''"><option value="">全部品項</option><option value="PART">零件 / 耗材</option><option value="LABOR">工資 / 服務費</option><option value="MAJOR_MAINTENANCE">大保養</option></select></label>
        <label><span>零件分類</span><select v-model="category" @change="manufacturer = ''"><option value="">全部分類</option><option v-for="entry in categories" :key="entry.value" :value="entry.value">{{ entry.name }}</option></select></label>
        <label><span>廠商</span><select v-model="manufacturer"><option value="">全部廠商</option><option v-for="name in manufacturers" :key="name" :value="name">{{ name }}</option></select></label>
      </div>
      <p class="quick-result-count" role="status">{{ matches.length }} 個品項<span>點選即可加入，可連續新增</span></p>
      <div class="quick-results">
        <button v-for="product in visibleProducts" :key="product.id" type="button" class="product-card" :disabled="disabled" @click="add(product)">
          <span class="product-meta">{{ product.manufacturer || typeLabels[product.inventory_type] || '零件 / 耗材' }}</span>
          <strong>{{ workOrderProductLabel(product) }}</strong>
          <span class="product-card-bottom"><span>NT$ {{ Number(product.price || 0).toLocaleString() }}</span><span class="add-symbol">＋</span></span>
        </button>
        <p v-if="!matches.length" class="quick-empty">沒有符合條件的商品，請調整搜尋或篩選。</p>
        <button v-if="matches.length > visibleCount" type="button" class="load-more" @click="visibleCount += 60">顯示更多商品</button>
      </div>
      <footer><span role="status" aria-live="polite">{{ lastAdded ? `已加入：${lastAdded}` : '選擇商品後，將帶入售價與數量。' }}</span><button type="button" @click="$emit('close')">完成選取<span v-if="addedCount">（{{ addedCount }}）</span></button></footer>
    </section>
  </div>
</template>
<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue';
import { categoryOptions, manufacturerOptions, filterWorkOrderProducts, searchWorkOrderProducts, workOrderProductLabel } from '../../utils/workOrderProductPicker';
const props = defineProps({ products: { type: Array, required: true }, disabled: Boolean });
const emit = defineEmits(['add', 'close']);
const query = ref(''), type = ref(''), category = ref(''), manufacturer = ref('');
const addedCount = ref(0), lastAdded = ref(''), visibleCount = ref(60), searchInput = ref(null), closeButton = ref(null);
const typeLabels = { LABOR: '工資 / 服務費', MAJOR_MAINTENANCE: '大保養' };
const catalog = computed(() => props.products.filter(product => ['PART', 'BOTH', 'LABOR', 'MAJOR_MAINTENANCE'].includes(product.inventory_type)
  && (!type.value || (type.value === 'PART' ? ['PART', 'BOTH'].includes(product.inventory_type) : product.inventory_type === type.value))));
const categories = computed(() => categoryOptions(catalog.value));
const manufacturers = computed(() => manufacturerOptions(catalog.value, category.value));
const matches = computed(() => searchWorkOrderProducts(filterWorkOrderProducts(catalog.value, category.value, manufacturer.value), query.value));
const visibleProducts = computed(() => matches.value.slice(0, visibleCount.value));
watch([query, type, category, manufacturer], () => { visibleCount.value = 60; });
function add(product) {
  if (props.disabled) return;
  emit('add', product);
  addedCount.value++;
  lastAdded.value = workOrderProductLabel(product);
}
let previousFocus;
function trapFocus(event) {
  if (event.key !== 'Tab') return;
  const panel = closeButton.value?.closest('.quick-panel');
  const targets = [...(panel?.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled)') || [])];
  const first = targets[0], last = targets.at(-1);
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
}
onMounted(() => {
  previousFocus = document.activeElement;
  searchInput.value?.focus();
  closeButton.value?.closest('.quick-panel')?.addEventListener('keydown', trapFocus);
});
onBeforeUnmount(() => {
  closeButton.value?.closest('.quick-panel')?.removeEventListener('keydown', trapFocus);
  previousFocus?.isConnected && previousFocus.focus();
});
</script>
<style scoped>
.quick-overlay { position: fixed; inset: 0; z-index: 1600; display: flex; justify-content: end; background: #000a; }
.quick-panel { display: flex; flex-direction: column; width: min(700px, 100%); height: 100dvh; background: var(--admin-surface, #181818); color: var(--admin-text, #eee); box-shadow: -12px 0 48px #0006; }
header { display: flex; align-items: center; justify-content: space-between; padding: 24px; border-bottom: 1px solid var(--admin-border, #363636); }
.eyebrow { font-size: 12px; color: var(--admin-danger, #ef7777); letter-spacing: .1em; }
h3 { margin: 6px 0 0; font-size: 22px; }
header button { border: 1px solid var(--admin-border, #444); border-radius: 6px; width: 40px; height: 40px; color: var(--admin-muted, #ccc); background: var(--admin-surface, #242424); font-size: 24px; cursor: pointer; }
.quick-filters { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; padding: 20px 24px 12px; }
label { display: grid; gap: 7px; min-width: 0; }
label span { font-size: 12px; color: var(--admin-muted, #aaa); }
.quick-search { grid-column: 1 / -1; }
input, select { box-sizing: border-box; width: 100%; min-width: 0; height: 42px; padding: 8px 10px; border: 1px solid var(--admin-border, #444); border-radius: 6px; background: var(--admin-surface, #242424); color: var(--admin-text, #eee); font: inherit; }
input:focus-visible, select:focus-visible, button:focus-visible { outline: 2px solid var(--admin-accent, #ef5350); outline-offset: 2px; }
.quick-result-count { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; padding: 0 24px; color: var(--admin-muted, #ccc); font-size: 12px; }
.quick-result-count span { color: var(--admin-muted, #888); }
.quick-results { flex: 1; overflow-y: auto; overscroll-behavior: contain; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); align-content: start; gap: 12px; padding: 8px 24px 24px; }
.product-card { display: flex; flex-direction: column; gap: 10px; text-align: left; padding: 16px; border: 1px solid var(--admin-border, #404040); border-radius: 8px; background: var(--admin-surface, #222); color: var(--admin-text, #eee); cursor: pointer; }
.product-card:hover { border-color: var(--admin-danger, #ef7777); background: var(--admin-surface, #2e2323); }
.product-card:disabled { opacity: .4; cursor: not-allowed; }
.product-meta { color: var(--admin-muted, #999); font-size: 11px; }
.product-card strong { line-height: 1.6; font-size: 14px; overflow-wrap: anywhere; }
.product-card-bottom { display: flex; align-items: center; justify-content: space-between; margin-top: auto; color: var(--admin-danger, #ef9999); font-size: 13px; }
.add-symbol { display: grid; place-items: center; width: 26px; height: 26px; background: rgba(var(--admin-accent-rgb, 239,83,80), 0.10196); border-radius: 5px; font-size: 18px; }
.load-more, .quick-empty { grid-column: 1 / -1; text-align: center; padding: 20px; color: var(--admin-muted, #aaa); }
.load-more { border: 1px solid var(--admin-border, #444); background: var(--admin-surface, #222); border-radius: 6px; cursor: pointer; }
footer { display: flex; gap: 12px; justify-content: space-between; align-items: center; border-top: 1px solid var(--admin-border, #444); padding: 18px 24px; background: var(--admin-surface, #202020); }
footer > span { font-size: 12px; color: var(--admin-muted, #aaa); overflow-wrap: anywhere; }
footer button { flex-shrink: 0; background: var(--admin-accent, #d83f3f); border: 0; color: #fff; padding: 12px 18px; border-radius: 6px; cursor: pointer; }
@media(max-width: 480px) { header, footer { padding: 16px; } .quick-filters { padding: 16px; gap: 8px; } .quick-results { padding: 0 16px 16px; gap: 8px; } .product-card { padding: 12px; } footer { padding-bottom: max(16px, env(safe-area-inset-bottom)); } }
</style>
