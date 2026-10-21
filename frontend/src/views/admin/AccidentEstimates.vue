<template>
  <div class="accident-estimates">
    <header class="page-heading"><div><h2>車禍估價單</h2><p>手動填寫估價內容，儲存並列印給客戶。</p></div><button :disabled="busy" @click="newEstimate">新增估價單</button></header>
    <form class="search-bar" @submit.prevent="searchList"><input v-model.trim="search" placeholder="搜尋客戶、電話或車牌" aria-label="搜尋估價單" /><button :disabled="loading">搜尋</button></form>
    <p v-if="listError" role="alert" class="error">{{ listError }}</p>
    <div class="table-scroll"><table class="list-table"><thead><tr><th>單號 / 估價日期</th><th>客戶</th><th>車牌 / 車種</th><th>總金額</th><th>操作</th></tr></thead><tbody>
      <tr v-for="estimate in estimates" :key="estimate.id"><td>#{{ estimate.id }}<br />{{ estimate.estimate_date }}</td><td>{{ estimate.customer_name }}<br />{{ estimate.phone }}</td><td>{{ estimate.license_plate || '—' }}<br />{{ estimate.vehicle_model }}</td><td>NT$ {{ money(estimate.total) }}</td><td><button :disabled="busy" @click="openEstimate(estimate.id)">編輯 / 列印</button></td></tr>
      <tr v-if="!estimates.length"><td colspan="5">{{ loading ? '載入中…' : '目前沒有估價單' }}</td></tr>
    </tbody></table></div>
    <div class="pagination"><button :disabled="loading || page === 0" @click="changePage(-1)">上一頁</button><span>第 {{ page + 1 }} 頁</span><button :disabled="loading || estimates.length < pageSize" @click="changePage(1)">下一頁</button></div>

    <form v-if="draft" ref="editor" class="estimate-editor" @submit.prevent="save">
      <header class="page-heading"><h3>{{ draft.id ? `估價單 #${draft.id}` : '新增車禍估價單' }} <small>{{ dirty ? '尚未儲存' : '已儲存' }}</small></h3><button type="button" :disabled="busy" @click="closeEditor">關閉</button></header>
      <fieldset :disabled="busy">
        <div class="field-grid">
          <label>店家名稱<input v-model.trim="draft.store_name" required maxlength="100" /></label>
          <label>客戶名稱<input v-model.trim="draft.customer_name" required maxlength="100" /></label>
          <label>聯絡電話<input v-model.trim="draft.phone" type="tel" maxlength="50" /></label>
          <label>牌照號碼<input v-model.trim="draft.license_plate" maxlength="30" /></label>
          <label>引擎號碼<input v-model.trim="draft.engine_number" maxlength="100" /></label>
          <label>車種<input v-model.trim="draft.vehicle_model" maxlength="100" /></label>
          <label>估價日期<input v-model="draft.estimate_date" type="date" required /></label>
          <label>開立日期<input v-model="draft.opened_date" type="date" required /></label>
          <label>估價人員<input v-model.trim="draft.estimator" maxlength="100" /></label>
        </div>
        <p class="hint">金額單位為新臺幣整元。小計＝零件售價 × 數量＋該列運費；總額另加安裝工資。</p>
        <div class="table-scroll"><table class="items-table"><thead><tr><th>項次</th><th>更換零件</th><th>零件售價</th><th>運費（整列）</th><th>數量</th><th>單位</th><th>小計</th><th>內部備註（不列印）</th><th></th></tr></thead><tbody>
          <tr v-for="(item, index) in draft.items" :key="index">
            <td>{{ index + 1 }}</td><td><input v-model.trim="item.name" :aria-label="`第${index + 1}項更換零件`" maxlength="200" /></td>
            <td><input v-model.number="item.unit_price" :aria-label="`第${index + 1}項零件售價`" type="number" min="0" max="100000000" step="1" required /></td>
            <td><input v-model.number="item.freight" :aria-label="`第${index + 1}項運費`" type="number" min="0" max="100000000" step="1" required /></td>
            <td><input v-model.number="item.quantity" :aria-label="`第${index + 1}項數量`" type="number" min="1" max="10000" step="1" required /></td>
            <td><input v-model.trim="item.unit" :aria-label="`第${index + 1}項單位`" maxlength="20" placeholder="個 / 組" /></td>
            <td class="amount">{{ money(subtotal(item)) }}</td><td><textarea v-model="item.internal_note" :aria-label="`第${index + 1}項內部備註`" maxlength="2000" rows="1" placeholder="料號等內部資訊" /></td>
            <td><button type="button" :aria-label="`刪除第${index + 1}項`" @click="draft.items.splice(index, 1)">刪除</button></td>
          </tr>
        </tbody></table></div>
        <button type="button" :disabled="draft.items.length >= 500" @click="draft.items.push(blankItem())">＋新增品項</button>
        <div class="summary"><label>安裝工資<input v-model.number="draft.labor" type="number" min="0" max="100000000" step="1" required /></label><strong>合計 NT$ {{ money(total) }}</strong></div>
        <label>列印說明<textarea v-model="draft.terms" rows="3" maxlength="3000" /></label>
        <label class="private-notes">內部備註（不列印）<textarea v-model="draft.internal_note" rows="3" maxlength="10000" placeholder="僅供店家查看，可填料號、供應商或其他內部資訊。" /></label>
      </fieldset>
      <p v-if="editorError" class="error" role="alert">{{ editorError }}</p><p v-if="notice" role="status">{{ notice }}</p>
      <div class="actions"><button type="submit" :disabled="busy">{{ busy ? '處理中…' : '儲存估價單' }}</button><button type="button" :disabled="busy" @click="preview">列印預覽</button></div>
    </form>

    <Teleport to="body"><div v-if="draft" class="estimate-preview-overlay" :class="{ 'is-visible': showPreview }" role="dialog" aria-modal="true" aria-labelledby="estimate-preview-title" @keydown.esc="showPreview = false">
      <div class="estimate-preview-toolbar"><h3 id="estimate-preview-title">車禍估價單列印預覽</h3><span>內部備註不會列印{{ dirty ? ' · 此預覽包含尚未儲存的修改' : '' }}</span><button @click="printEstimate">列印 / 另存 PDF</button><button ref="previewClose" @click="showPreview = false">關閉預覽</button></div>
      <!-- Only this public document is copied into the print frame. Private notes never enter it. -->
      <div ref="printDocument" class="estimate-print-document"><article class="estimate-paper">
        <header class="estimate-paper-heading"><div class="estimate-paper-brand" aria-label="GFmotor">GF<span>motor</span></div><div><h1>{{ draft.store_name }}</h1><h2>車禍估價單</h2></div></header>
        <div class="estimate-paper-fields"><span>客戶名稱：{{ draft.customer_name }}</span><span>聯絡電話：{{ draft.phone }}</span><span>牌照號碼：{{ draft.license_plate }}</span><span>引擎號碼：{{ draft.engine_number }}</span><span>車種：{{ draft.vehicle_model }}</span><span>估價日期：{{ draft.estimate_date }}</span></div>
        <div class="estimate-paper-date">開立日期：{{ draft.opened_date }}</div>
        <table class="estimate-paper-table"><colgroup><col style="width:7%" /><col style="width:35%" /><col style="width:14%" /><col style="width:11%" /><col style="width:10%" /><col style="width:9%" /><col style="width:14%" /></colgroup>
          <thead><tr><th>項次</th><th>更換零件</th><th>零件售價</th><th>運費</th><th>數量(數字)</th><th>數量單位</th><th>小計</th></tr></thead>
          <tbody><tr v-for="(item, index) in printRows" :key="index"><td>{{ index + 1 }}</td><td class="part-name">{{ item?.name }}</td><td>{{ item ? money(item.unit_price) : '' }}</td><td>{{ item ? money(item.freight) : '' }}</td><td>{{ item?.quantity }}</td><td>{{ item?.unit }}</td><td>{{ item ? money(subtotal(item)) : '0' }}</td></tr></tbody>
          <tbody class="estimate-paper-totals"><tr><th colspan="2">安裝工資</th><td colspan="5">{{ money(draft.labor) }}</td></tr><tr><th colspan="2">合計</th><td colspan="5"><strong>{{ money(total) }}</strong></td></tr></tbody>
        </table>
        <footer class="estimate-paper-footer"><div class="estimate-paper-terms">說明：{{ draft.terms }}</div><div class="estimate-paper-signatures"><span>估價人員：{{ draft.estimator }}</span><span>客戶簽名：</span></div></footer>
      </article></div>
    </div></Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import api from '../../api';
import { useSiteStore } from '../../store/site';
import printStyles from '../../assets/accidentEstimatePrint.css?inline';
import '../../assets/accidentEstimatePrint.css';

const site = useSiteStore();
const estimates = ref([]), search = ref(''), page = ref(0), loading = ref(false), busy = ref(false);
const listError = ref(''), editorError = ref(''), notice = ref(''), draft = ref(null), snapshot = ref('');
const editor = ref(null), showPreview = ref(false), printDocument = ref(null), previewClose = ref(null);
const pageSize = 50, endpoint = '/admin/accident-estimates';
let printFrame = null;
let requestSequence = 0;
const blankItem = () => ({ name: '', unit_price: 0, freight: 0, quantity: 1, unit: '', internal_note: '' });
const money = value => Number(value || 0).toLocaleString('zh-TW');
const subtotal = item => (Number(item.unit_price) || 0) * (Number(item.quantity) || 0) + (Number(item.freight) || 0);
const total = computed(() => draft.value ? draft.value.items.reduce((sum, item) => sum + subtotal(item), 0) + (Number(draft.value.labor) || 0) : 0);
const dirty = computed(() => draft.value && JSON.stringify(draft.value) !== snapshot.value);
const printRows = computed(() => Array.from({ length: Math.max(34, draft.value?.items.length || 0) }, (_, index) => draft.value.items[index] || null));
const canDiscard = () => !dirty.value || window.confirm('估價單有尚未儲存的修改，確定放棄修改？');
const message = error => typeof error.response?.data?.detail === 'string' ? error.response.data.detail : '操作失敗，請檢查資料或連線後重試。';
const setDraft = data => { draft.value = data; snapshot.value = JSON.stringify(data); editorError.value = ''; notice.value = ''; };
const today = () => { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`; };
async function loadList() {
  const sequence = ++requestSequence;
  loading.value = true; listError.value = '';
  try { const data = await api.get(`${endpoint}/`, { params: { q: search.value, skip: page.value * pageSize, limit: pageSize } }); if (sequence === requestSequence) estimates.value = data; }
  catch (error) { if (sequence === requestSequence) listError.value = message(error); }
  finally { if (sequence === requestSequence) loading.value = false; }
}
function searchList() { page.value = 0; loadList(); }
function changePage(direction) { page.value += direction; loadList(); }
async function newEstimate() {
  if (!canDiscard()) return;
  setDraft({ store_name: site.settings.store_name, customer_name: '', phone: '', license_plate: '', vehicle_model: '', engine_number: '', estimate_date: today(), opened_date: today(), items: [blankItem()], labor: 0, estimator: '', terms: '本估價單經雙方簽章後生效，視同為買賣合約。\n估價單開發後如未在本店維修酌收費用為1500元整。', internal_note: '' });
  // A newly opened form must also be protected against accidental navigation.
  snapshot.value = '';
  await nextTick(); editor.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
async function openEstimate(id) {
  if (!canDiscard()) return;
  busy.value = true; listError.value = '';
  try { setDraft(await api.get(`${endpoint}/${id}`)); await nextTick(); editor.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
  catch (error) { listError.value = message(error); }
  finally { busy.value = false; }
}
function closeEditor() { if (canDiscard()) draft.value = null; }
async function save() {
  busy.value = true; editorError.value = ''; notice.value = '';
  try {
    const saved = draft.value.id ? await api.put(`${endpoint}/${draft.value.id}`, draft.value) : await api.post(`${endpoint}/`, draft.value);
    setDraft(saved); notice.value = '估價單已儲存'; await loadList();
  } catch (error) { editorError.value = message(error); }
  finally { busy.value = false; }
}
async function preview() {
  if (!editor.value.reportValidity()) return;
  showPreview.value = true; await nextTick(); previewClose.value?.focus();
}
async function printEstimate() {
  printFrame?.remove();
  const frame = document.createElement('iframe');
  printFrame = frame; frame.title = '車禍估價單列印';
  frame.style.cssText = 'position:fixed;width:0;height:0;border:0;';
  document.body.appendChild(frame);
  const doc = frame.contentDocument;
  doc.open(); doc.write('<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>車禍估價單</title></head><body></body></html>'); doc.close();
  const style = doc.createElement('style'); style.textContent = printStyles; doc.head.appendChild(style);
  doc.body.appendChild(printDocument.value.cloneNode(true));
  await Promise.all([...doc.images].map(img => img.decode().catch(() => {})));
  await doc.fonts.ready;
  frame.contentWindow.onafterprint = () => { frame.remove(); if (printFrame === frame) printFrame = null; };
  frame.contentWindow.focus(); frame.contentWindow.print();
}
function beforeUnload(event) { if (dirty.value) { event.preventDefault(); event.returnValue = ''; } }
watch(showPreview, value => { document.body.classList.toggle('estimate-preview-open', value); if (!value) nextTick(() => editor.value?.querySelector('.actions button:last-child')?.focus()); });
onBeforeRouteLeave(() => !busy.value && canDiscard());
onMounted(() => { document.body.classList.add('accident-estimate-page'); loadList(); window.addEventListener('beforeunload', beforeUnload); });
onBeforeUnmount(() => { printFrame?.remove(); document.body.classList.remove('estimate-preview-open', 'accident-estimate-page'); window.removeEventListener('beforeunload', beforeUnload); });
</script>

<style scoped>
.accident-estimates { color: #e5e7eb; }
.page-heading, .search-bar, .pagination, .actions, .summary { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.page-heading { justify-content: space-between; margin-bottom: 20px; }
h2, h3, p { margin: 0; } p, small { color: #aeb6c4; } small { font-size: 13px; font-weight: normal; }
button { padding: 9px 15px; border: 1px solid #72512c; border-radius: 6px; background: #c78b38; color: #111827; font: inherit; cursor: pointer; }
button:disabled { opacity: .5; cursor: wait; }
input, textarea { box-sizing: border-box; width: 100%; border: 1px solid #4b5563; border-radius: 5px; background: #151922; color: #f9fafb; padding: 9px; font: inherit; }
input:focus, textarea:focus { outline: 2px solid #dca44c; outline-offset: 1px; }
textarea { resize: vertical; }
.search-bar { margin-bottom: 15px; }.search-bar input { max-width: 360px; }
.table-scroll { overflow-x: auto; margin-bottom: 14px; }
table { width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; } th, td { border-bottom: 1px solid #394150; padding: 10px; }
th { color: #c4cad4; white-space: nowrap; }.list-table { min-width: 580px; }
.pagination { justify-content: flex-end; margin: 15px 0 28px; }
.estimate-editor { padding: 24px; border: 1px solid #4b5563; background: #202630; border-radius: 10px; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
.field-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
label { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.hint { font-size: 13px; margin: 12px 0; }.items-table { min-width: 1150px; }.items-table input[type=number] { min-width: 85px; }.items-table td:nth-child(2) { min-width: 180px; }.items-table td:nth-child(6) { min-width: 85px; }.items-table td:nth-child(8) { min-width: 180px; }.amount { white-space: nowrap; }
.summary { justify-content: flex-end; margin: 20px 0; }.summary label { width: 180px; }.summary strong { font-size: 24px; color: #f5c873; }
.private-notes { background: #292e40; padding: 15px; border-left: 3px solid #a9a4df; }.actions { margin-top: 20px; }.error { color: #ffabab; padding: 12px 0; }
@media(max-width: 800px) { .field-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }.estimate-editor { padding: 14px; } }
@media(max-width: 480px) { .field-grid { grid-template-columns: 1fr; } }
</style>
