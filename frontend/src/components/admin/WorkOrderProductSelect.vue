<template>
  <div class="search-select" @focusout="handleFocusOut" @keydown.esc.stop.prevent="close">
    <input :id="inputId" ref="input" role="combobox" aria-label="商品名稱" autocomplete="off"
      aria-autocomplete="list" aria-haspopup="listbox" :aria-expanded="open" :aria-controls="listId"
      :aria-activedescendant="open && activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined"
      :value="open ? query : selectedLabel" :title="selectedLabel" :disabled="disabled"
      placeholder="選擇或搜尋商品" @focus="show" @click="show" @input="search($event.target.value)"
      @keydown.down.prevent="move(1)" @keydown.up.prevent="move(-1)" @keydown.enter="confirm" />
    <ul v-if="open && !disabled" :id="listId" role="listbox" aria-label="商品選項">
      <li v-for="(product, index) in results" :id="`${listId}-${index}`" :key="product.id"
        role="option" :aria-selected="Number(modelValue) === product.id" :class="{ active: activeIndex === index }"
        @pointerdown.prevent="startOptionPointer" @pointermove="moveOptionPointer"
        @pointercancel="cancelOptionPointer" @pointerup="finishOptionPointer($event, product)"
        @click="select(product)">{{ workOrderProductLabel(product) }}</li>
      <li v-if="!results.length" class="empty" role="presentation">沒有符合的商品</li>
    </ul>
    <span class="sr-only" role="status">{{ open ? `找到 ${results.length} 個商品` : '' }}</span>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, useId, watch } from 'vue';
import { searchWorkOrderProducts, workOrderProductLabel } from '../../utils/workOrderProductPicker';
const props = defineProps({
  products: { type: Array, required: true }, modelValue: Number, disabled: Boolean,
  fallbackLabel: { type: String, default: '' }
});
const emit = defineEmits(['select']);
const inputId = useId();
const listId = `${inputId}-options`;
const input = ref(null);
const open = ref(false);
const query = ref('');
const activeIndex = ref(-1);
let optionPointer = null;
const selectedLabel = computed(() => {
  const product = props.products.find(product => product.id === Number(props.modelValue));
  return product ? workOrderProductLabel(product) : props.modelValue ? props.fallbackLabel : '';
});
const results = computed(() => searchWorkOrderProducts(props.products, query.value));
watch(() => [props.products, props.modelValue, props.disabled], close);
function close() { open.value = false; query.value = ''; activeIndex.value = -1; optionPointer = null; }
function show() {
  if (props.disabled || open.value) return;
  query.value = '';
  activeIndex.value = -1;
  open.value = true;
}
function search(value) { query.value = value; open.value = true; activeIndex.value = -1; }
async function move(direction) {
  show();
  if (!results.value.length) return;
  activeIndex.value = activeIndex.value < 0
    ? direction > 0 ? 0 : results.value.length - 1
    : (activeIndex.value + direction + results.value.length) % results.value.length;
  await nextTick();
  input.value?.ownerDocument.getElementById(`${listId}-${activeIndex.value}`)?.scrollIntoView({ block: 'nearest' });
}
function confirm(event) {
  if (event.isComposing) return;
  event.preventDefault();
  if (open.value && activeIndex.value >= 0 && results.value[activeIndex.value]) select(results.value[activeIndex.value]);
}
function select(product) { emit('select', product.id); close(); }
// Safari can omit the click after a prevented touch pointerdown. Commit taps
// on pointerup as well, but leave scrolling and canceled gestures unselected.
function startOptionPointer(event) {
  optionPointer = event.isPrimary && event.button === 0 && event.pointerType !== 'mouse'
    ? { id: event.pointerId, x: event.clientX, y: event.clientY, target: event.currentTarget }
    : null;
}
function moveOptionPointer(event) {
  if (optionPointer?.id === event.pointerId
    && Math.hypot(event.clientX - optionPointer.x, event.clientY - optionPointer.y) > 10) {
    optionPointer = null;
  }
}
function cancelOptionPointer() { optionPointer = null; }
function finishOptionPointer(event, product) {
  moveOptionPointer(event);
  const pointer = optionPointer;
  optionPointer = null;
  if (!pointer || pointer.id !== event.pointerId) return;
  const hit = event.currentTarget.ownerDocument.elementFromPoint(event.clientX, event.clientY);
  if (pointer.target === event.currentTarget && pointer.target.contains(hit)) {
    event.preventDefault();
    select(product);
  }
}
function handleFocusOut(event) { if (!event.currentTarget.contains(event.relatedTarget)) close(); }
</script>

<style scoped>
.search-select { position: relative; min-width: 0; }
input { width: 100%; min-width: 0; height: 38px; box-sizing: border-box; border: 1px solid #444; border-radius: 6px; background: #202124; color: #eee; padding: .45rem .65rem; font: inherit; }
input:focus-visible { outline: 2px solid #ef5350; outline-offset: 1px; }
input:disabled { opacity: .6; }
ul { position: absolute; z-index: 20; top: 100%; left: 0; right: 0; max-height: 260px; overflow-y: auto; overscroll-behavior: contain; margin: .25rem 0 0; padding: .25rem; list-style: none; background: #202124; color: #eee; border: 1px solid #666; border-radius: 6px; box-shadow: 0 4px 12px #0008; }
li { padding: .65rem .5rem; min-height: 44px; box-sizing: border-box; overflow-wrap: anywhere; cursor: pointer; }
li.active, li:hover:not(.empty) { background: #52292b; }
li[aria-selected=true] { font-weight: 700; }
li.empty { cursor: default; color: #bbb; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
</style>
