<template>
  <div class="sheet-lines">
    <div v-if="!items.length" class="empty-lines">尚無消費明細，請新增項目或使用「商品快速點選」。</div>
    <div v-for="(item, index) in items" :key="itemKey(item)" class="sheet-line" :class="{ 'part-line': item.type === 'PART', 'discount-line': item.type === 'DISCOUNT', 'named-line': ['LABOR', 'DISCOUNT'].includes(item.type), 'has-points': showPoints && manageMembership && member && item.type === 'PART', dragging: draggedItem === item }"
      @dragover.prevent @drop.prevent="drop(item)">
      <div class="row-number" :draggable="!disabled && !busy" title="拖曳排序" @dragstart="startDrag($event, item)" @dragend="draggedItem = null"><span class="row-dots" aria-hidden="true">⠿</span>{{ String(index + 1).padStart(2, '0') }}</div>
      <WorkOrderProductPicker :item="item" :products="products" :types="types" :disabled="rowLocked(item)"
        @select-product="$emit('select-product', $event)" @change-type="$emit('change-type', $event)" />
      <label v-if="['LABOR', 'DISCOUNT'].includes(item.type)" class="name-field">
        <span>明細名稱</span><input v-model.trim="item.name" :disabled="rowLocked(item)" placeholder="明細名稱" required />
      </label>
      <label class="quantity-field"><span>數量</span><input v-model.number="item.quantity" type="number" min="1" step="1" required :disabled="rowLocked(item)" /></label>
      <label class="price-field"><span>售價</span>
        <input v-if="canEnterDetails(item)" v-model.number="item.unit_price" type="number" min="0" :disabled="rowLocked(item)" />
        <span v-else class="field-value">{{ money(item.unit_price) }}</span>
      </label>
      <label v-if="manageMembership" class="membership-field" title="消費可累積點數">
        <span>累積消費</span><input v-model="item.counts_toward_membership" type="checkbox" :disabled="disabled || membershipLocked || Boolean(item.promotion_gift_id)" />
      </label>
      <div class="amount-field"><span>小計</span><strong>{{ money(lineItemTotal(item)) }}</strong></div>
      <div v-if="!disabled" class="row-actions">
        <button type="button" class="remove" title="刪除明細" aria-label="刪除明細" :disabled="rowLocked(item)" @click="$emit('remove', index)">×</button>
      </div>
      <label v-if="showPoints && manageMembership && member && item.type === 'PART'" class="points-field">
        <input type="checkbox" :checked="Number(item.points_redeemed || 0) > 0" :disabled="disabled || locked || Boolean(item.promotion_gift_id)"
          @change="$emit('toggle-points', item, $event.target.checked)" />
        <span>使用點數</span><input v-model.number="item.points_redeemed" type="number" min="1" :max="redeemablePoints"
          :disabled="disabled || locked || Number(item.points_redeemed || 0) <= 0 || Boolean(item.promotion_gift_id)" /><span>點</span>
      </label>
      <small v-if="item.promotion_name || item.promotion_gift_id" class="promotion-note">{{ item.promotion_gift_id ? '活動贈品' : item.promotion_name }}</small>
    </div>
  </div>
</template>

<script setup>
import WorkOrderProductPicker from './WorkOrderProductPicker.vue';
import { ref } from 'vue';
import { lineItemTotal } from '../../utils/workOrderAmounts';
const props = defineProps({
  items: { type: Array, required: true }, products: { type: Array, required: true }, types: { type: Object, required: true },
  itemKey: { type: Function, required: true }, canEnterDetails: { type: Function, required: true },
  inventoryLocked: { type: Function, default: () => false }, disabled: Boolean, locked: Boolean, membershipLocked: Boolean,
  busy: Boolean, manageMembership: Boolean, showPoints: Boolean, member: Boolean, redeemablePoints: { type: Number, default: 0 },
});
const emit = defineEmits(['select-product', 'change-type', 'remove', 'move', 'toggle-points']);
const draggedItem = ref(null);
function startDrag(event, item) {
  if (props.disabled || props.busy) { event.preventDefault(); return; }
  draggedItem.value = item;
  event.dataTransfer.effectAllowed = 'move';
  event.dataTransfer.setData('text/plain', String(props.items.indexOf(item)));
}
function drop(item) {
  const from = props.items.indexOf(draggedItem.value), to = props.items.indexOf(item);
  draggedItem.value = null;
  if (!props.disabled && !props.busy && from >= 0 && to >= 0 && from !== to) emit('move', from, to - from);
}
const rowLocked = item => props.disabled || props.locked || props.inventoryLocked(item) || Boolean(item.promotion_gift_id);
const money = value => `NT$ ${Number(value || 0).toLocaleString()}`;
</script>

<style scoped>
.sheet-lines { min-height: 230px; container-type: inline-size; }
.sheet-line { display: grid; grid-template-columns: 32px 100px minmax(90px, .8fr) minmax(90px, .8fr) minmax(160px, 1.8fr) 64px 90px 64px 104px 36px; align-items: end; gap: 10px; padding: 16px 0; border-bottom: 1px solid var(--admin-border, #363636); }
.sheet-line:focus-within { background: rgba(var(--admin-ink-rgb, 255,255,255), 0.01176); }
.sheet-line.dragging { opacity: .5; }
.sheet-line :deep(.search-select:focus-within) { z-index: 26; }
.sheet-line :deep(.product-picker) { display: contents; }
.sheet-line :deep(.picker-type) { grid-column: 2; }
.sheet-line :deep(.picker-manufacturer) { grid-column: 3; }
.sheet-line :deep(.picker-category) { grid-column: 4; }
.sheet-line :deep(.product-field) { grid-column: 5; }
.sheet-line :deep(.picker-type), .sheet-line :deep(.picker-manufacturer), .sheet-line :deep(.picker-category), .sheet-line :deep(.product-field) { grid-row: 1; }
.row-number { grid-column: 1; grid-row: 1; display: grid; justify-items: center; align-content: center; height: 42px; color: var(--admin-muted, #919191); font-size: 11px; font-variant-numeric: tabular-nums; }
.row-dots { font-size: 22px; line-height: 18px; color: var(--admin-muted, #666); }
.row-number[draggable=true] { cursor: grab; }
label, .amount-field { display: grid; gap: 6px; min-width: 0; }
label > span, .amount-field > span { color: var(--admin-muted, #aaa); font-size: 12px; font-weight: 600; }
input:not([type=checkbox]), .field-value { box-sizing: border-box; width: 100%; min-width: 0; height: 38px; padding: 8px; border: 1px solid var(--admin-border, #444); border-radius: 6px; background: var(--admin-surface, #202124); color: var(--admin-text, #eee); font: inherit; font-size: 13px; }
input:focus-visible { outline: 2px solid var(--admin-accent, #ef5350); outline-offset: 1px; }
input:disabled { opacity: .55; }
.field-value { display: flex; align-items: center; white-space: nowrap; }
.quantity-field { grid-column: 6; grid-row: 1; }
.price-field { grid-column: 7; grid-row: 1; }
.membership-field { grid-column: 8; grid-row: 1; justify-items: center; white-space: nowrap; }
input[type=checkbox] { width: 18px; height: 18px; accent-color: var(--admin-accent, #ef5350); margin: 10px 0; }
.amount-field { grid-column: 9; grid-row: 1; text-align: right; }
.amount-field strong { display: flex; justify-content: end; align-items: center; min-height: 38px; font-size: 14px; white-space: nowrap; }
.discount-line .amount-field strong { color: var(--admin-success, #82c991); }
.row-actions { grid-column: 10; grid-row: 1; display: flex; gap: 4px; min-height: 38px; align-items: center; justify-content: end; }
.row-actions button { border: 1px solid var(--admin-border, #444); border-radius: 5px; background: var(--admin-surface, #222); color: var(--admin-muted, #ccc); width: 30px; height: 34px; cursor: pointer; }
.row-actions button:disabled { opacity: .3; cursor: not-allowed; }
.row-actions .remove { color: var(--admin-danger, #ef7777); }
.name-field { grid-column: 3 / 6; grid-row: 2; }
.points-field { grid-column: 6 / -1; grid-row: 2; display: flex; justify-content: end; align-items: center; gap: 8px; }
.points-field input[type=number] { width: 70px; }
.promotion-note { grid-column: 2 / -1; color: var(--admin-warning, #dbb67c); font-size: 12px; }
.empty-lines { display: grid; place-items: center; min-height: 210px; color: var(--admin-muted, #999); font-size: 14px; text-align: center; }
.sheet-line:not(.part-line) :deep(.picker-manufacturer),
.sheet-line:not(.part-line) :deep(.picker-category),
.discount-line :deep(.product-field) { display: none; }
@container (min-width: 1081px) {
  .has-points { grid-template-columns: 28px 100px minmax(80px, .7fr) minmax(80px, .7fr) minmax(160px, 1.8fr) 56px 84px 64px 96px 160px 36px; gap: 8px; }
  .has-points .points-field { grid-column: 10; grid-row: 1; justify-content: center; min-height: 38px; gap: 5px; }
  .has-points .points-field input[type=number] { width: 58px; }
  .has-points .row-actions { grid-column: 11; }
}
@container (max-width: 1080px) {
  .sheet-line { grid-template-columns: 28px 100px minmax(90px, 1fr) minmax(90px, 1fr) minmax(140px, 1.6fr); gap: 10px; }
  .quantity-field { grid-column: 2; grid-row: 2; }
  .price-field { grid-column: 3; grid-row: 2; }
  .membership-field { grid-column: 4; grid-row: 2; justify-items: start; }
  .amount-field { grid-column: 5; grid-row: 2; }
  .row-actions { grid-column: 5; grid-row: 3; }
  .name-field { grid-column: 2 / 5; grid-row: 3; }
  .points-field { grid-column: 2 / -1; grid-row: 4; }
}
@container (min-width: 900px) {
  .sheet-line:not(.part-line) { grid-template-columns: 28px 110px minmax(130px, 1fr) minmax(130px, 1fr) 56px 84px 64px 96px 36px; gap: 8px; }
  .sheet-line:not(.part-line) :deep(.product-field) { grid-column: 3 / 5; grid-row: 1; }
  .sheet-line.named-line:not(.discount-line) :deep(.product-field) { grid-column: 3; }
  .sheet-line.named-line:not(.discount-line) .name-field { grid-column: 4; grid-row: 1; }
  .sheet-line.discount-line .name-field { grid-column: 3 / 5; grid-row: 1; }
  .sheet-line:not(.part-line) .quantity-field { grid-column: 5; grid-row: 1; }
  .sheet-line:not(.part-line) .price-field { grid-column: 6; grid-row: 1; }
  .sheet-line:not(.part-line) .membership-field { grid-column: 7; grid-row: 1; justify-items: center; }
  .sheet-line:not(.part-line) .amount-field { grid-column: 8; grid-row: 1; }
  .sheet-line:not(.part-line) .row-actions { grid-column: 9; grid-row: 1; }
}
@container (min-width: 621px) and (max-width: 899px) {
  .sheet-line:not(.part-line) :deep(.product-field) { grid-column: 3 / -1; }
  .sheet-line.discount-line .name-field { grid-column: 2 / -1; grid-row: 1; margin-left: 110px; }
}
@container (max-width: 620px) {
  .sheet-line { grid-template-columns: 24px repeat(2, minmax(0, 1fr)); gap: 12px 10px; padding: 18px 0; }
  .row-number { grid-row: 1 / 3; align-self: start; }
  .sheet-line :deep(.picker-type) { grid-column: 2; grid-row: 1; }
  .sheet-line :deep(.picker-manufacturer) { grid-column: 3; grid-row: 1; }
  .sheet-line :deep(.picker-category) { grid-column: 2; grid-row: 2; }
  .sheet-line :deep(.product-field) { grid-column: 2 / -1; grid-row: 3; }
  .name-field { grid-column: 2 / -1; grid-row: 4; }
  .quantity-field { grid-column: 2; grid-row: 5; }
  .price-field { grid-column: 3; grid-row: 5; }
  .membership-field { grid-column: 2; grid-row: 6; display: flex; gap: 8px; align-items: center; }
  .amount-field { grid-column: 3; grid-row: 6; }
  .points-field { grid-column: 2 / -1; grid-row: 7; justify-content: start; flex-wrap: wrap; }
  .row-actions { grid-column: 2 / -1; grid-row: 8; }
  .row-actions button { width: 40px; height: 40px; }
  .promotion-note { grid-column: 2 / -1; }
}
</style>
