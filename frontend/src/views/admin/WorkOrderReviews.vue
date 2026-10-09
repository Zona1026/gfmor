<template>
  <div v-if="canReview" class="work-order-reviews">
    <div class="section-header">
      <div><h2>待復核工單</h2><p>集中查看工單明細、庫存狀態與待審核項目。</p></div>
      <button class="btn" :disabled="loading" @click="fetchReviews()">重新整理</button>
    </div>
    <form class="search-row" @submit.prevent="fetchReviews()">
      <input v-model.trim="search" type="search" placeholder="搜尋工單號、客戶、電話或車牌" aria-label="搜尋待復核工單" />
      <button class="btn" :disabled="loading">搜尋</button>
    </form>
    <p v-if="errorMessage" role="alert" class="error-message">{{ errorMessage }}</p>
    <div class="table-wrap">
      <table v-if="workOrders.length">
        <thead><tr><th>工單</th><th>客戶 / 車牌</th><th>待復核內容</th><th>總金額</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="workOrder in workOrders" :key="workOrder.id">
            <td>#{{ workOrder.id }}</td>
            <td>{{ workOrder.customer_name || '-' }}<span class="secondary-line">{{ workOrder.vehicle_license_plate || '-' }}</span></td>
            <td>{{ reviewReasons(workOrder) }}</td>
            <td>NT$ {{ (workOrder.total_amount || 0).toLocaleString() }}</td>
            <td><button class="btn btn-primary" :disabled="opening" @click="openReview(workOrder.id)">查看復核</button></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-state">{{ loading ? '載入中...' : errorMessage ? '無法載入工單，請重新整理。' : '目前沒有待復核工單。' }}</p>
    </div>
    <button v-if="hasMore" class="btn load-more" :disabled="loading" @click="fetchReviews(true)">載入更多</button>

    <div v-if="selectedWorkOrder" class="modal-overlay" @click.self="closeReview">
      <div class="review-modal" role="dialog" aria-modal="true" aria-labelledby="review-title">
        <div class="section-header">
          <div><h3 id="review-title">復核工單 #{{ selectedWorkOrder.id }}</h3><p>{{ selectedWorkOrder.customer_name || '-' }} / {{ selectedWorkOrder.vehicle_license_plate || '-' }}</p></div>
          <button class="btn" :disabled="busy" aria-label="關閉復核" @click="closeReview">×</button>
        </div>
        <dl class="review-summary">
          <div><dt>服務類型</dt><dd>{{ serviceTypeMap[selectedWorkOrder.service_type] || selectedWorkOrder.service_type }}</dd></div>
          <div><dt>負責人</dt><dd>{{ selectedWorkOrder.responsible_staff || '-' }}</dd></div>
          <div><dt>問題描述</dt><dd>{{ selectedWorkOrder.problem_description || '-' }}</dd></div>
          <div><dt>檢查結果</dt><dd>{{ selectedWorkOrder.inspection_result || '-' }}</dd></div>
          <div><dt>備註</dt><dd>{{ selectedWorkOrder.notes || '-' }}</dd></div>
          <div><dt>總金額</dt><dd>NT$ {{ (selectedWorkOrder.total_amount || 0).toLocaleString() }}</dd></div>
          <div><dt>可列入會員累積</dt><dd>NT$ {{ (selectedWorkOrder.membership_eligible_amount || 0).toLocaleString() }}</dd></div>
        </dl>
        <section v-if="pendingApprovals.length">
          <h4>待審核項目</h4>
          <ul class="approval-list">
            <li v-for="approval in pendingApprovals" :key="approval.id">
              <div><strong>{{ approvalTypeMap[approval.type] || approval.type }}</strong><p>{{ approval.reason || approval.title }}</p></div>
              <button class="btn" :disabled="busy" @click="rejectApproval(approval)">退回</button>
            </li>
          </ul>
        </section>
        <section>
          <div class="section-header">
            <h4>明細狀態</h4>
            <button v-if="!selectedWorkOrder.supervisor_reviewed_at || pendingApprovals.length" class="btn btn-primary" :disabled="busy" @click="confirmReview">{{ reviewing ? '審核中...' : '確認審核' }}</button>
            <span v-else>已審核</span>
          </div>
          <div class="table-wrap">
            <table v-if="selectedWorkOrder.line_items?.length">
              <thead><tr><th>類型</th><th>名稱</th><th>單價 / 數量</th><th>累積消費 / 點數</th><th>庫存數量</th><th>狀態</th><th>最後更新時間</th></tr></thead>
              <tbody>
                <tr v-for="item in selectedWorkOrder.line_items" :key="item.id">
                  <td>{{ lineItemTypeMap[item.type] || item.type }}</td>
                  <td>{{ item.name }}</td>
                  <td>NT$ {{ (item.unit_price || 0).toLocaleString() }} / {{ item.quantity }}</td>
                  <td>{{ item.counts_toward_membership ? '列入累積' : '不列入累積' }}<span class="secondary-line">使用 {{ item.points_redeemed || 0 }} 點</span></td>
                  <td>{{ item.type === 'PART' ? inventoryStatusText(item) : '-' }}</td>
                  <td><select :value="item.fulfillment_status || ''" :disabled="busy" :aria-label="`${item.name}明細狀態`" @change="updateFulfillment(item, $event.target.value)"><option value="" disabled>請選擇</option><option v-for="(label, value) in fulfillmentStatusMap" :key="value" :value="value">{{ label }}</option></select></td>
                  <td>{{ formatTaipeiDateTime(item.fulfillment_status_updated_at || item.created_at) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="empty-state">目前沒有工單明細。</p>
          </div>
        </section>
        <p v-if="actionError" class="error-message" role="alert">{{ actionError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useAuthStore } from '../../store/auth';
import { getWorkOrderReviews, getWorkOrderReview, confirmWorkOrderReview, rejectWorkOrderApproval, updateWorkOrderLineItemFulfillmentStatus } from '../../api/admin';
import { formatTaipeiDateTime } from '../../utils/dateTime';

const router = useRouter();
const { adminUser } = storeToRefs(useAuthStore());
const canReview = computed(() => adminUser.value?.role === '最高級');
const workOrders = ref([]);
const selectedWorkOrder = ref(null);
const search = ref('');
const loading = ref(false);
const opening = ref(false);
const reviewing = ref(false);
const updating = ref(false);
const busy = computed(() => reviewing.value || updating.value);
const hasMore = ref(false);
const errorMessage = ref('');
const actionError = ref('');
const pageSize = 50;
const pendingApprovals = computed(() => (selectedWorkOrder.value?.approvals || []).filter(item => item.status === 'PENDING'));
const approvalTypeMap = { DISCOUNT: '折扣', HIGH_QUOTE: '高額報價', STATUS_CHANGE: '狀態變更', INVENTORY_RESERVATION: '確認預留', INVENTORY_CONSUMPTION: '確認扣庫存' };
const lineItemTypeMap = { PART: '零件 / 耗材', LABOR: '工資', SERVICE: '施工 / 服務', DISCOUNT: '折扣' };
const serviceTypeMap = { REPAIR: '維修', MAINTENANCE: '保養', MODIFICATION: '改裝' };
const reviewReasons = (order) => {
  const labels = (order.approvals || []).filter(item => item.status === 'PENDING').map(item => approvalTypeMap[item.type] || item.type);
  if (!order.supervisor_reviewed_at) labels.unshift('工單明細復核');
  return [...new Set(labels)].join('、') || '主管復核';
};
const messageFor = (error) => {
  const detail = error.response?.data?.detail;
  return typeof detail === 'string' ? detail : '操作失敗，請稍後重試。';
};
const handlePermissionError = (error) => {
  if ([401, 403].includes(error.response?.status)) {
    workOrders.value = [];
    selectedWorkOrder.value = null;
    router.replace(error.response.status === 401 ? '/admin-login' : '/admin/work-orders');
    return true;
  }
  return false;
};
const fetchReviews = async (append = false) => {
  if (!canReview.value || loading.value) return;
  loading.value = true;
  errorMessage.value = '';
  try {
    const rows = await getWorkOrderReviews({ skip: append ? workOrders.value.length : 0, limit: pageSize, q: search.value || undefined });
    if (!canReview.value) return;
    workOrders.value = append ? [...workOrders.value, ...rows] : rows;
    hasMore.value = rows.length === pageSize;
  } catch (error) {
    if (!handlePermissionError(error)) errorMessage.value = messageFor(error);
  } finally { loading.value = false; }
};
const openReview = async (id) => {
  if (!canReview.value || opening.value) return;
  opening.value = true;
  actionError.value = '';
  try {
    const order = await getWorkOrderReview(id);
    if (canReview.value) selectedWorkOrder.value = order;
  } catch (error) {
    if (!handlePermissionError(error)) errorMessage.value = messageFor(error);
  } finally { opening.value = false; }
};
const closeReview = () => { if (!busy.value) selectedWorkOrder.value = null; };
const updateFulfillment = async (item, status) => {
  if (!canReview.value || busy.value || !status) return;
  updating.value = true;
  actionError.value = '';
  try { selectedWorkOrder.value = await updateWorkOrderLineItemFulfillmentStatus(selectedWorkOrder.value.id, item.id, status); }
  catch (error) { if (!handlePermissionError(error)) actionError.value = messageFor(error); }
  finally { updating.value = false; }
};
const confirmReview = async () => {
  if (!canReview.value || busy.value || !selectedWorkOrder.value) return;
  reviewing.value = true;
  actionError.value = '';
  try {
    await confirmWorkOrderReview(selectedWorkOrder.value.id);
    selectedWorkOrder.value = null;
    await fetchReviews();
  } catch (error) { if (!handlePermissionError(error)) actionError.value = messageFor(error); }
  finally { reviewing.value = false; }
};
const rejectApproval = async (approval) => {
  if (!canReview.value || busy.value) return;
  const note = window.prompt('請輸入退回原因');
  if (!note?.trim()) return;
  updating.value = true;
  actionError.value = '';
  try {
    await rejectWorkOrderApproval(approval.id, { note: note.trim() });
    const order = await getWorkOrderReview(selectedWorkOrder.value.id);
    selectedWorkOrder.value = order;
    await fetchReviews();
  } catch (error) { if (!handlePermissionError(error)) actionError.value = messageFor(error); }
  finally { updating.value = false; }
};

const inventoryStatusText = (item) => {
  const reserved = Number(item.inventory_reserved_quantity || 0);
  const consumed = Number(item.inventory_consumed_quantity || 0);
  const shortage = Number(item.inventory_shortage_quantity || 0);
  const activeRequests = (item.purchase_requests || []).filter(request => !['CANCELED', 'ASSIGNED_TO_WORK_ORDER'].includes(request.status));
  const quantity = Number(item.quantity || 0);

  if (consumed >= quantity && quantity > 0) return `已扣庫存 ${consumed}`;
  if (selectedWorkOrder.value?.inventory_reservation_pending && reserved <= 0 && consumed <= 0) return '待主管確認預留';
  if (selectedWorkOrder.value?.inventory_consumption_pending && reserved > 0) return `待主管確認扣庫存 / 已預留 ${reserved}`;
  if (shortage > 0 && activeRequests.length) return `已預留 ${reserved} / 已扣 ${consumed} / 缺貨待到貨 ${shortage}`;
  if (shortage > 0) return `已預留 ${reserved} / 已扣 ${consumed} / 缺貨 ${shortage}`;
  if (reserved > 0) return `已預留 ${reserved} / 待扣庫存`;
  if (consumed > 0) return `已扣庫存 ${consumed}`;
  return '尚未預留';
};


const fulfillmentStatusMap = {
  PENDING: '確認中',
  RESERVED: '已預留',
  ORDERED: '已叫貨',
  ARRIVED: '已到貨'
};
watch(canReview, (allowed) => {
  if (!allowed) {
    workOrders.value = [];
    selectedWorkOrder.value = null;
    router.replace('/admin/work-orders');
  }
});
onMounted(() => fetchReviews());
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';
.work-order-reviews {
  color: $text-primary;
  .section-header, .search-row { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1rem; }
  h2, h3, h4 { margin: 0; color: $primary-light; }
  p { color: $text-secondary; }
  .search-row input { flex: 1; min-width: 180px; }
  .btn, input, select { padding: 0.6rem 0.8rem; border: 1px solid $medium-grey; border-radius: $border-radius; background: $dark-grey; color: $text-primary; font: inherit; }
  .btn { cursor: pointer; }
  .btn-primary { background: $primary-color; border-color: $primary-color; color: #fff; }
  :disabled { opacity: 0.55; cursor: not-allowed; }
  .table-wrap { overflow: auto; border: 1px solid $medium-grey; border-radius: $border-radius; }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 0.8rem; text-align: left; border-bottom: 1px solid $medium-grey; vertical-align: top; }
  th { color: $text-secondary; background: $background-color; white-space: nowrap; }
  td select { min-width: 110px; }
  .secondary-line { display: block; color: $text-secondary; font-size: 0.85rem; margin-top: 0.3rem; }
  .empty-state { text-align: center; padding: 2rem; }
  .load-more { margin-top: 1rem; }
  .error-message { color: #ffb74d; }
  .modal-overlay { position: fixed; inset: 0; z-index: 1000; overflow-y: auto; padding: 2rem 1rem; background: rgba(0, 0, 0, 0.7); }
  .review-modal { box-sizing: border-box; width: min(100%, 1180px); margin: 0 auto; padding: 1.5rem; background: $dark-grey; border: 1px solid $medium-grey; border-radius: $border-radius; }
  .review-summary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.8rem; }
  .review-summary div { min-width: 0; }
  dt { color: $text-secondary; }
  dd { margin: 0.3rem 0 0; overflow-wrap: anywhere; }
  section { margin-top: 1.5rem; }
  .approval-list { list-style: none; padding: 0; }
  .approval-list li { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: 0.75rem 0; border-bottom: 1px solid $medium-grey; }
  @media (max-width: 700px) { .review-summary { grid-template-columns: 1fr; } .review-modal { padding: 1rem; } }
}
</style>
