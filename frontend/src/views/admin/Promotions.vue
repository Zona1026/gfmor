<template>
  <div class="promotions">
    <div class="section-header">
      <h2>{{ history ? '過往活動' : '活動設定' }}</h2>
      <div class="actions">
        <button type="button" class="btn btn-outline" :disabled="loading" @click="load">重新整理</button>
        <button v-if="!history && canManage" type="button" class="btn btn-primary" @click="open()">＋ 新增活動</button>
      </div>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="loading">載入中…</p>
    <template v-else>
      <section v-for="group in groups" :key="group.status" class="activity-group">
        <h3>{{ group.title }} <span>（{{ group.items.length }}）</span></h3>
        <p v-if="!group.items.length" class="empty">{{ group.empty }}</p>
        <div class="cards">
          <article v-for="activity in group.items" :key="activity.id" class="activity-card">
            <h4>{{ activity.name }}</h4>
            <p class="description">{{ activity.description }}</p>
            <p class="discount">{{ discountLabel(activity) }}</p>
            <p>期間：{{ displayTime(activity.starts_at) }} ～ {{ displayTime(activity.ends_at) }}</p>
            <p>{{ activity.discount_type === 'BOGO' ? '購買商品 A' : '適用商品' }}：{{ activity.products.map(product => product.name).join('、') || '商品已移除' }}</p>
            <div v-if="canManage && !history" class="actions">
              <button type="button" class="btn btn-outline" @click="open(activity)">編輯</button>
              <button type="button" class="btn btn-outline" :disabled="busy" @click="finish(activity)">結束活動</button>
            </div>
          </article>
        </div>
      </section>
    </template>
    <div v-if="showForm" class="modal-overlay" @click.self="!saving && (showForm = false)">
      <section class="activity-modal" role="dialog" aria-modal="true" aria-labelledby="activity-form-title">
        <h3 id="activity-form-title">{{ editingId ? '編輯活動' : '新增活動' }}</h3>
        <form @submit.prevent="save">
          <label>活動名稱<input v-model.trim="form.name" required maxlength="100" /></label>
          <label>活動說明<textarea v-model="form.description" rows="3" maxlength="5000" /></label>
          <div class="form-grid">
            <label>開始時間（台灣時間）<input v-model="form.starts_at" type="datetime-local" required /></label>
            <label>結束時間（台灣時間）<input v-model="form.ends_at" type="datetime-local" required /></label>
            <label>折扣方式<select v-model="form.discount_type"><option value="PERCENT">百分比折扣</option><option value="AMOUNT">每件折抵金額</option><option value="BOGO">買A送B</option></select></label>
            <label v-if="form.discount_type !== 'BOGO'">{{ form.discount_type === 'PERCENT' ? '減免百分比（10 表示 9 折）' : '每件折抵（NT$）' }}<span class="number-with-unit"><input v-model.number="form.discount_value" type="number" min="1" :max="form.discount_type === 'PERCENT' ? 100 : 1000000" step="1" required /><span v-if="form.discount_type === 'PERCENT'" class="unit" aria-hidden="true">%</span></span></label>
            <label v-else>購買數量門檻（件）<input v-model.number="form.buy_quantity" type="number" min="1" max="1000000" step="1" required /></label>
          </div>
          <label class="checkbox"><input v-model="form.is_active" type="checkbox" />啟用活動</label>
          <PromotionProductSelector v-model="form.product_ids" :products="products" :fallback="form.products || []" :disabled="saving" :title="form.discount_type === 'BOGO' ? '購買商品 A（可複選，數量合計）' : '適用商品（可複選）'" />
          <template v-if="form.discount_type === 'BOGO'">
            <PromotionProductSelector v-model="form.gift_product_ids" :products="products" :fallback="form.gift_product ? [form.gift_product] : []" :disabled="saving" title="贈品 B" :multiple="false" />
            <label>每達門檻贈送數量（件）<input v-model.number="form.gift_quantity" type="number" min="1" max="1000000" step="1" required /></label>
            <label class="checkbox"><input v-model="form.allow_discount_stacking" type="checkbox" />可與百分比／金額折扣並用</label>
          </template>
          <p class="tip">{{ form.discount_type === 'BOGO' ? '達到購買數量門檻後，自動加入零元贈品明細，依工單庫存流程扣庫存。' : '工單選取商品時自動帶入活動價；多個活動採最低價、不疊加，單價最低為 NT$ 0。' }}</p>
          <p v-if="formError" class="error" role="alert">{{ formError }}</p>
          <div class="actions"><button type="button" class="btn btn-outline" :disabled="saving" @click="showForm = false">取消</button><button class="btn btn-primary" :disabled="saving">{{ saving ? '儲存中…' : '儲存活動' }}</button></div>
        </form>
      </section>
    </div>
  </div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '../../store/auth';
import { getPromotions, createPromotion, updatePromotion, endPromotion, getInventoryItems } from '../../api/admin';
import PromotionProductSelector from '../../components/admin/PromotionProductSelector.vue';
const route = useRoute();
const auth = useAuthStore();
const history = computed(() => Boolean(route.meta.promotionHistory));
const canManage = computed(() => ['最高級', '管理層'].includes(auth.adminUser?.role));
const activities = ref([]), products = ref([]), loading = ref(false), error = ref('');
const showForm = ref(false), editingId = ref(null), saving = ref(false), busy = ref(false), formError = ref('');
const form = reactive({});
const groups = computed(() => (history.value
  ? [{ status: 'ENDED', title: '已結束活動', empty: '目前沒有過往活動。' }]
  : [{ status: 'CURRENT', title: '現行活動', empty: '目前沒有現行活動。' }, { status: 'SCHEDULED', title: '即將開始', empty: '目前沒有預定活動。' }, { status: 'DISABLED', title: '停用活動', empty: '目前沒有停用活動。' }]
).map(group => ({ ...group, items: activities.value.filter(activity => activity.status === group.status) })));
function displayTime(value) { return new Date(value).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false }); }
function localTime(value) {
  const date = new Date(new Date(value).getTime() + 8 * 60 * 60 * 1000);
  return date.toISOString().slice(0, 16);
}
function discountLabel(activity) { if (activity.discount_type === 'BOGO') return `買 ${activity.buy_quantity} 件送 ${activity.gift_quantity} 件：${activity.gift_product?.name || '贈品已移除'}${activity.allow_discount_stacking ? '（可與折扣並用）' : ''}`; return activity.discount_type === 'PERCENT' ? `減免 ${activity.discount_value}%` : `每件折抵 NT$ ${activity.discount_value.toLocaleString()}`; }
function message(err) { return typeof err.response?.data?.detail === 'string' ? err.response.data.detail : '操作失敗，請確認設定後重試。'; }
async function load() {
  loading.value = true; error.value = '';
  try { const data = await Promise.all([getPromotions(), getInventoryItems({ type: 'all' })]); activities.value = data[0]; products.value = data[1]; }
  catch (err) { error.value = message(err); }
  finally { loading.value = false; }
}
function open(activity) {
  editingId.value = activity?.id || null; formError.value = '';
  Object.assign(form, activity ? { ...activity, starts_at: localTime(activity.starts_at), ends_at: localTime(activity.ends_at), product_ids: [...activity.product_ids], gift_product_ids: activity.gift_product_id ? [activity.gift_product_id] : [], buy_quantity: activity.buy_quantity || 1, gift_quantity: activity.gift_quantity || 1, allow_discount_stacking: Boolean(activity.allow_discount_stacking) }
    : { name: '', description: '', starts_at: localTime(Date.now()), ends_at: localTime(Date.now() + 7 * 86400000), discount_type: 'PERCENT', discount_value: 10, is_active: true, product_ids: [], gift_product_ids: [], buy_quantity: 1, gift_quantity: 1, allow_discount_stacking: false });
  showForm.value = true;
}
async function save() {
  if (saving.value) return;
  formError.value = '';
  const starts = new Date(form.starts_at + ':00+08:00'), ends = new Date(form.ends_at + ':00+08:00');
  if (!form.name || !form.product_ids.length || !(ends > starts) || ends <= new Date()) { formError.value = '請填寫活動名稱、選擇商品，並設定有效的活動期間。'; return; }
  if (form.discount_type === 'BOGO' && !form.gift_product_ids.length) { formError.value = '請設定贈品 B。'; return; }
  saving.value = true;
  try {
    const payload = { name: form.name, description: form.description, starts_at: starts.toISOString(), ends_at: ends.toISOString(), discount_type: form.discount_type, discount_value: form.discount_value, is_active: form.is_active, product_ids: form.product_ids, buy_quantity: form.buy_quantity, gift_quantity: form.gift_quantity, gift_product_id: form.discount_type === 'BOGO' ? form.gift_product_ids[0] : null, allow_discount_stacking: form.discount_type === 'BOGO' && form.allow_discount_stacking };
    if (editingId.value) await updatePromotion(editingId.value, payload); else await createPromotion(payload);
    showForm.value = false; await load();
  } catch (err) { formError.value = message(err); }
  finally { saving.value = false; }
}
async function finish(activity) {
  if (busy.value || !window.confirm(`結束「${activity.name}」？結束後會移到過往活動，且不再套用折扣。`)) return;
  busy.value = true;
  try { await endPromotion(activity.id); await load(); } catch (err) { error.value = message(err); }
  finally { busy.value = false; }
}
watch(() => route.path, () => { showForm.value = false; load(); });
let refresh;
onMounted(() => { load(); refresh = window.setInterval(() => { if (!showForm.value && !loading.value) load(); }, 60000); });
onUnmounted(() => window.clearInterval(refresh));
</script>
<style scoped>
.section-header, .actions { display: flex; align-items: center; gap: .65rem; flex-wrap: wrap; }
.section-header { justify-content: space-between; margin-bottom: 1.2rem; }
.btn { padding: .65rem .9rem; border: 1px solid #444; border-radius: 8px; background: #222; color: #eee; font: inherit; cursor: pointer; }
.btn-primary { background: #e53935; border-color: #e53935; color: white; }
.btn:disabled { opacity: .5; cursor: default; }
.btn:focus-visible { outline: 2px solid #ffb74d; outline-offset: 2px; }
h2, h3 { color: #ef4444; } h4 { font-size: 1.1rem; margin: 0; }
.activity-group { margin-bottom: 1.8rem; } .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 1rem; }
.activity-card { padding: 1.2rem; border: 1px solid #444; background: #161616; border-radius: 8px; overflow-wrap: anywhere; }
.description { white-space: pre-wrap; } .discount { color: #ffb74d; font-weight: bold; }
.empty, .tip { color: #bbb; } .error { color: #ffb74d; }
.modal-overlay { position: fixed; inset: 0; z-index: 1000; background: #000a; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.activity-modal { width: 720px; max-width: 100%; max-height: calc(100dvh - 2rem); overflow-y: auto; background: #222; padding: 1.3rem; border: 1px solid #444; border-radius: 8px; box-sizing: border-box; }
form { display: grid; gap: 1rem; } label { display: grid; gap: .4rem; } input, textarea, select { min-width: 0; width: 100%; box-sizing: border-box; background: #111; color: #eee; padding: .65rem; border: 1px solid #444; border-radius: 6px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.checkbox { display: flex; align-items: center; gap: .5rem; } .checkbox input { width: auto; }
fieldset { min-width: 0; border: 1px solid #555; border-radius: 6px; padding: .8rem; } .product-list { display: grid; gap: .65rem; max-height: 180px; overflow-y: auto; }
.number-with-unit { position: relative; display: flex; align-items: center; }
.number-with-unit input { padding-right: 3rem; }
.unit { position: absolute; right: 1.6rem; pointer-events: none; color: #ddd; }
.product-picker { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .65rem; margin-bottom: .8rem; }
.selected-product { display: flex; justify-content: space-between; align-items: center; gap: .65rem; }
.selected-product span { overflow-wrap: anywhere; }
@media (max-width: 600px) { .form-grid, .number-with-unit { position: relative; display: flex; align-items: center; }
.number-with-unit input { padding-right: 3rem; }
.unit { position: absolute; right: 1.6rem; pointer-events: none; color: #ddd; }
.product-picker { grid-template-columns: 1fr; } }
</style>
