<template>
  <div class="admin-purchases">
    <div class="section-header">
      <div>
        <h2>採購 / 叫貨管理</h2>
        <p>工單缺料、待到貨與到貨分配</p>
      </div>
      <div class="header-actions">
        <button v-if="canManagePurchases" class="btn btn-primary" type="button" @click="openCreateForm">
          ＋ 新增採購單
        </button>
        <button class="btn btn-outline" type="button" @click="fetchRequests">重新整理</button>
      </div>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
        <span>{{ counts[tab.key] || 0 }}</span>
      </button>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else class="table-wrap">
      <table v-if="filteredRequests.length" class="purchase-table">
        <thead>
          <tr>
            <th>項目名稱</th>
            <th>需求數量</th>
            <th>已到貨</th>
            <th>客戶 / 工單</th>
            <th>工單狀態</th>
            <th>預計到貨日</th>
            <th>狀態</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="request in filteredRequests" :key="request.id">
            <td>
              <strong>{{ request.item_name }}</strong>
              <small>{{ request.product?.name || `#${request.product_id}` }}</small>
            </td>
            <td>{{ request.requested_quantity }}</td>
            <td>{{ request.arrived_quantity }}</td>
            <td>{{ customerRef(request) }}</td>
            <td>
              <span class="status-tag" :class="request.work_order?.status">
                {{ workOrderStatusMap[request.work_order?.status] || request.work_order?.status || '-' }}
              </span>
            </td>
            <td>{{ formatDate(request.expected_arrival_date) }}</td>
            <td>
              <span class="status-tag" :class="request.status">
                {{ statusMap[request.status] || request.status }}
              </span>
            </td>
            <td>
              <div class="row-actions">
                <button class="btn text" type="button" @click="openDetail(request)">詳情</button>
                <button
                  v-if="canManagePurchases && request.status === 'PENDING_ORDER'"
                  class="btn text"
                  type="button"
                  @click="openOrderForm(request)"
                >
                  已叫貨
                </button>
                <button
                  v-if="canReceive(request)"
                  class="btn text"
                  type="button"
                  @click="openReceiveForm(request)"
                >
                  到貨
                </button>
                <button
                  v-if="canCancel(request)"
                  class="btn text danger"
                  type="button"
                  @click="cancelRequest(request)"
                >
                  取消
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">目前沒有資料</div>
    </div>

    <div v-if="showCreateForm" class="modal-overlay" @click.self="closeCreateForm">
      <form class="modal-content small" @submit.prevent="submitCreate">
        <div class="modal-header">
          <h3>新增採購單</h3>
          <button class="icon-btn" type="button" aria-label="關閉" @click="closeCreateForm">×</button>
        </div>
        <label>
          採購品項
          <select v-model="createForm.product_id" required>
            <option value="" disabled>請選擇商品或零件</option>
            <option v-for="item in inventoryItems" :key="item.id" :value="String(item.id)">
              {{ item.name }}（{{ inventoryTypeLabel(item.inventory_type) }}）
            </option>
          </select>
        </label>
        <label>
          採購數量
          <input v-model.number="createForm.quantity" type="number" min="1" required />
        </label>
        <label>
          供應商
          <input v-model.trim="createForm.supplier_name" />
        </label>
        <label>
          預計到貨日
          <input v-model="createForm.expected_arrival_date" type="date" />
        </label>
        <label>
          負責人
          <input v-model.trim="createForm.responsible_staff" />
        </label>
        <label>
          備註
          <textarea v-model.trim="createForm.note" rows="3"></textarea>
        </label>
        <div class="form-actions">
          <button class="btn btn-outline" type="button" @click="closeCreateForm">取消</button>
          <button class="btn btn-primary" type="submit" :disabled="saving">{{ saving ? '新增中...' : '確認新增' }}</button>
        </div>
      </form>
    </div>

    <div v-if="selectedRequest" class="modal-overlay" @click.self="closeDetail">
      <div class="modal-content">
        <div class="modal-header">
          <div>
            <h3>{{ selectedRequest.item_name }}</h3>
            <p>{{ customerRef(selectedRequest) }}</p>
          </div>
          <button class="icon-btn" type="button" @click="closeDetail">×</button>
        </div>

        <div class="detail-grid">
          <section class="detail-panel">
            <h4>叫貨資料</h4>
            <dl>
              <div><dt>供應商</dt><dd>{{ selectedRequest.supplier_name || '-' }}</dd></div>
              <div><dt>需求數量</dt><dd>{{ selectedRequest.requested_quantity }}</dd></div>
              <div><dt>已叫貨</dt><dd>{{ selectedRequest.ordered_quantity }}</dd></div>
              <div><dt>已到貨</dt><dd>{{ selectedRequest.arrived_quantity }}</dd></div>
              <div><dt>已分配</dt><dd>{{ selectedRequest.assigned_quantity }}</dd></div>
              <div><dt>預計到貨日</dt><dd>{{ formatDate(selectedRequest.expected_arrival_date) }}</dd></div>
              <div><dt>負責人</dt><dd>{{ selectedRequest.responsible_staff || '-' }}</dd></div>
              <div><dt>備註</dt><dd>{{ selectedRequest.note || '-' }}</dd></div>
            </dl>
          </section>

          <section class="detail-panel">
            <h4>對應工單</h4>
            <dl>
              <div><dt>工單</dt><dd>{{ selectedRequest.work_order_id ? `#${selectedRequest.work_order_id}` : '未綁定' }}</dd></div>
              <div><dt>客戶</dt><dd>{{ selectedRequest.customer_name || '-' }}</dd></div>
              <div><dt>電話</dt><dd>{{ selectedRequest.customer_phone || '-' }}</dd></div>
              <div><dt>車牌 / 設備</dt><dd>{{ selectedRequest.vehicle_license_plate || '-' }}</dd></div>
              <div><dt>明細</dt><dd>{{ selectedRequest.work_order_line_item_id ? `#${selectedRequest.work_order_line_item_id}` : '未綁定' }}</dd></div>
            </dl>
          </section>
        </div>

        <section class="detail-panel">
          <h4>到貨紀錄</h4>
          <table v-if="selectedRequest.receipts?.length" class="mini-table">
            <thead>
              <tr><th>時間</th><th>實收品項</th><th>數量</th><th>操作者</th><th>替代原因 / 備註</th></tr>
            </thead>
            <tbody>
              <tr v-for="receipt in selectedRequest.receipts" :key="receipt.id">
                <td>{{ formatDateTime(receipt.received_at) }}</td>
                <td>
                  {{ receipt.received_product?.name || selectedRequest.product?.name || '-' }}
                  <small v-if="receipt.received_product_id && receipt.received_product_id !== selectedRequest.product_id">替代品</small>
                </td>
                <td>{{ receipt.quantity }}</td>
                <td>{{ receipt.actor || '-' }}</td>
                <td>{{ receipt.substitution_reason || receipt.note || '-' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="muted-line">尚無到貨紀錄</div>
        </section>

        <section class="detail-panel">
          <h4>分配紀錄</h4>
          <form
            v-if="canManagePurchases && selectedRequest.unassigned_arrived_quantity > 0"
            class="assign-form"
            @submit.prevent="submitAssign"
          >
            <label>
              工單 ID
              <input v-model.number="assignForm.work_order_id" type="number" min="1" required />
            </label>
            <label>
              工單明細 ID
              <input v-model.number="assignForm.work_order_line_item_id" type="number" min="1" required />
            </label>
            <label>
              數量
              <input
                v-model.number="assignForm.quantity"
                type="number"
                min="1"
                :max="selectedRequest.unassigned_arrived_quantity"
                required
              />
            </label>
            <label>
              備註
              <input v-model.trim="assignForm.note" />
            </label>
            <button class="btn btn-primary" type="submit" :disabled="saving">分配</button>
          </form>
          <table v-if="selectedRequest.assignments?.length" class="mini-table">
            <thead>
              <tr><th>時間</th><th>工單</th><th>明細</th><th>數量</th><th>操作者</th></tr>
            </thead>
            <tbody>
              <tr v-for="assignment in selectedRequest.assignments" :key="assignment.id">
                <td>{{ formatDateTime(assignment.assigned_at) }}</td>
                <td>#{{ assignment.work_order_id }}</td>
                <td>#{{ assignment.work_order_line_item_id }}</td>
                <td>{{ assignment.quantity }}</td>
                <td>{{ assignment.actor || '-' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="muted-line">尚無分配紀錄</div>
        </section>
      </div>
    </div>

    <div v-if="orderingRequest" class="modal-overlay" @click.self="closeOrderForm">
      <form class="modal-content small" @submit.prevent="submitOrder">
        <div class="modal-header">
          <h3>登記已叫貨</h3>
          <button class="icon-btn" type="button" @click="closeOrderForm">×</button>
        </div>
        <label>
          供應商
          <input v-model.trim="orderForm.supplier_name" />
        </label>
        <label>
          已叫貨數量
          <input v-model.number="orderForm.ordered_quantity" type="number" min="1" required />
        </label>
        <label>
          預計到貨日
          <input v-model="orderForm.expected_arrival_date" type="date" />
        </label>
        <label>
          負責人
          <input v-model.trim="orderForm.responsible_staff" />
        </label>
        <label>
          備註
          <textarea v-model.trim="orderForm.note" rows="3"></textarea>
        </label>
        <div class="form-actions">
          <button class="btn btn-outline" type="button" @click="closeOrderForm">取消</button>
          <button class="btn btn-primary" type="submit" :disabled="saving">儲存</button>
        </div>
      </form>
    </div>

    <div v-if="receivingRequest" class="modal-overlay" @click.self="closeReceiveForm">
      <form class="modal-content small" @submit.prevent="submitReceive">
        <div class="modal-header">
          <h3>登記到貨</h3>
          <button class="icon-btn" type="button" @click="closeReceiveForm">×</button>
        </div>
        <label>
          到貨數量
          <input v-model.number="receiveForm.quantity" type="number" min="1" required />
        </label>
        <div class="receive-mode" role="group" aria-label="到貨品項模式">
          <button type="button" :class="{ active: !receiveForm.is_substitution }" @click="setReceiveMode(false)">原品項到貨</button>
          <button type="button" :class="{ active: receiveForm.is_substitution }" @click="setReceiveMode(true)">替代料件到貨</button>
        </div>
        <template v-if="receiveForm.is_substitution">
          <label>
            實際收到的料件
            <select v-model.number="receiveForm.received_product_id" required>
              <option :value="null" disabled>請選擇替代料件</option>
              <option v-for="item in substituteItems" :key="item.id" :value="item.id">
                {{ item.name }}（可用 {{ item.available_stock }}）
              </option>
            </select>
          </label>
          <label>
            替代原因
            <textarea v-model.trim="receiveForm.substitution_reason" rows="3" required placeholder="例如：原廠改送可通用的 B 料件"></textarea>
          </label>
          <label v-if="receivingRequest.work_order_line_item_id" class="check-row">
            <input v-model="receiveForm.replace_work_order_line_item" type="checkbox" />
            同步將來源工單明細改為實收料件
          </label>
          <label v-if="receiveForm.replace_work_order_line_item">
            替代料件工單單價（客戶計價）
            <input v-model.number="receiveForm.replacement_unit_price" type="number" min="0" required />
          </label>
          <p class="muted-hint">若清單沒有這個料件，請先到「庫存管理 / 零件列表」新增。</p>
        </template>
        <label>
          操作者
          <input v-model.trim="receiveForm.actor" readonly />
        </label>
        <label>
          備註
          <textarea v-model.trim="receiveForm.note" rows="3"></textarea>
        </label>
        <div class="form-actions">
          <button class="btn btn-outline" type="button" @click="closeReceiveForm">取消</button>
          <button class="btn btn-primary" type="submit" :disabled="saving">儲存</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useRoute } from 'vue-router';
import {
  assignPurchaseRequest,
  cancelPurchaseRequest,
  createPurchaseRequest,
  getInventoryItems,
  getPurchaseRequest,
  getPurchaseRequests,
  orderPurchaseRequest,
  receivePurchaseRequest
} from '../../api/admin';
import { useAuthStore } from '../../store/auth';

const route = useRoute();
const authStore = useAuthStore();
const { adminUser } = storeToRefs(authStore);
const canManagePurchases = computed(() => ['最高級', '管理層'].includes(adminUser.value?.role));
const canUseCriticalPurchase = computed(() => adminUser.value?.role === '最高級');

const tabs = [
  { key: 'pending-order', label: '待叫貨' },
  { key: 'awaiting-arrival', label: '已叫貨 / 待到貨' },
  { key: 'partial-arrived', label: '部分到貨' },
  { key: 'pending-assignment', label: '已到貨待分配' },
  { key: 'assigned', label: '已分配到工單' }
];

const statusMap = {
  PENDING_ORDER: '待叫貨',
  ORDERED: '已叫貨 / 待到貨',
  PARTIAL_ARRIVED: '部分到貨',
  ARRIVED_PENDING_ASSIGNMENT: '已到貨待分配',
  ASSIGNED_TO_WORK_ORDER: '已分配到工單',
  CANCELED: '已取消'
};

const workOrderStatusMap = {
  PENDING: '待處理',
  INSPECTION_PENDING: '待檢查',
  QUOTE_PENDING: '待報價',
  CUSTOMER_CONFIRMATION_PENDING: '等待客戶確認',
  SUPERVISOR_APPROVAL_PENDING: '待主管確認',
  IN_PROGRESS: '施工中',
  AWAITING_PAYMENT: '待收款',
  COMPLETED: '已完工',
  CANCELED: '已取消'
};

const tabStatusMap = {
  'pending-order': ['PENDING_ORDER'],
  'awaiting-arrival': ['ORDERED'],
  'partial-arrived': ['PARTIAL_ARRIVED'],
  'pending-assignment': ['ARRIVED_PENDING_ASSIGNMENT'],
  assigned: ['ASSIGNED_TO_WORK_ORDER']
};

const loading = ref(false);
const saving = ref(false);
const requests = ref([]);
const activeTab = ref(route.query.status || 'pending-order');
const selectedRequest = ref(null);
const orderingRequest = ref(null);
const receivingRequest = ref(null);
const showCreateForm = ref(false);
const inventoryItems = ref([]);

const defaultCreateForm = () => ({
  product_id: '',
  quantity: 1,
  supplier_name: '',
  expected_arrival_date: '',
  responsible_staff: '',
  note: ''
});
const createForm = reactive(defaultCreateForm());

const orderForm = reactive({
  supplier_name: '',
  ordered_quantity: 1,
  expected_arrival_date: '',
  responsible_staff: '',
  note: ''
});

const receiveForm = reactive({
  quantity: 1,
  is_substitution: false,
  received_product_id: null,
  replace_work_order_line_item: false,
  replacement_unit_price: 0,
  substitution_reason: '',
  actor: '',
  note: ''
});

const assignForm = reactive({
  work_order_id: null,
  work_order_line_item_id: null,
  quantity: 1,
  note: ''
});

const filteredRequests = computed(() => {
  const statuses = tabStatusMap[activeTab.value] || [];
  return requests.value.filter(request => statuses.includes(request.status));
});

const counts = computed(() => {
  const result = {};
  for (const tab of tabs) {
    const statuses = tabStatusMap[tab.key] || [];
    result[tab.key] = requests.value.filter(request => statuses.includes(request.status)).length;
  }
  return result;
});

const substituteItems = computed(() => inventoryItems.value.filter(item =>
  item.id !== receivingRequest.value?.product_id && ['PART', 'BOTH'].includes(item.inventory_type)
));

const fetchRequests = async () => {
  loading.value = true;
  try {
    requests.value = await getPurchaseRequests({ limit: 500 });
  } catch (error) {
    console.error('載入叫貨需求失敗:', error);
    alert(error.response?.data?.detail || '載入叫貨需求失敗');
  } finally {
    loading.value = false;
  }
};

const customerRef = (request) => {
  if (!request.work_order_id) return '庫存補貨 / 未綁工單';
  const customer = request.customer_name || '-';
  return `${customer} / 工單 #${request.work_order_id}`;
};

const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`;
};

const formatDateTime = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return `${formatDate(value)} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const inventoryTypeLabel = (type) => {
  const labels = { SHOP: '商品', PART: '零件', BOTH: '共用' };
  return labels[type] || type;
};

const openCreateForm = async () => {
  Object.assign(createForm, defaultCreateForm());
  showCreateForm.value = true;
  if (!inventoryItems.value.length) {
    try {
      inventoryItems.value = await getInventoryItems({ type: 'all' });
    } catch (error) {
      alert(error.response?.data?.detail || '載入庫存品項失敗');
      showCreateForm.value = false;
    }
  }
};

const closeCreateForm = () => {
  showCreateForm.value = false;
};

const submitCreate = async () => {
  saving.value = true;
  try {
    await createPurchaseRequest({
      product_id: Number(createForm.product_id),
      quantity: createForm.quantity,
      supplier_name: createForm.supplier_name || null,
      expected_arrival_date: createForm.expected_arrival_date ? `${createForm.expected_arrival_date}T00:00:00` : null,
      responsible_staff: createForm.responsible_staff || null,
      note: createForm.note || null
    });
    activeTab.value = 'awaiting-arrival';
    closeCreateForm();
    await fetchRequests();
  } catch (error) {
    alert(error.response?.data?.detail || '新增採購單失敗');
  } finally {
    saving.value = false;
  }
};

const canReceive = (request) => canUseCriticalPurchase.value && ['ORDERED', 'PARTIAL_ARRIVED', 'ARRIVED_PENDING_ASSIGNMENT'].includes(request.status);
const canCancel = (request) => canManagePurchases.value && ['PENDING_ORDER', 'ORDERED', 'PARTIAL_ARRIVED'].includes(request.status) && !request.assigned_quantity;

const refreshOne = async (id) => {
  const updated = await getPurchaseRequest(id);
  const index = requests.value.findIndex(item => item.id === id);
  if (index >= 0) requests.value.splice(index, 1, updated);
  if (selectedRequest.value?.id === id) selectedRequest.value = updated;
  return updated;
};

const openDetail = async (request) => {
  selectedRequest.value = await getPurchaseRequest(request.id);
  assignForm.work_order_id = selectedRequest.value.work_order_id || null;
  assignForm.work_order_line_item_id = selectedRequest.value.work_order_line_item_id || null;
  assignForm.quantity = Math.max(1, selectedRequest.value.unassigned_arrived_quantity || 1);
  assignForm.note = '';
};

const closeDetail = () => {
  selectedRequest.value = null;
};

const openOrderForm = (request) => {
  orderingRequest.value = request;
  orderForm.supplier_name = request.supplier_name || '';
  orderForm.ordered_quantity = request.requested_quantity || 1;
  orderForm.expected_arrival_date = request.expected_arrival_date ? request.expected_arrival_date.slice(0, 10) : '';
  orderForm.responsible_staff = request.responsible_staff || '';
  orderForm.note = request.note || '';
};

const closeOrderForm = () => {
  orderingRequest.value = null;
};

const submitOrder = async () => {
  if (!orderingRequest.value) return;
  saving.value = true;
  try {
    await orderPurchaseRequest(orderingRequest.value.id, {
      supplier_name: orderForm.supplier_name || null,
      ordered_quantity: orderForm.ordered_quantity,
      expected_arrival_date: orderForm.expected_arrival_date ? `${orderForm.expected_arrival_date}T00:00:00` : null,
      responsible_staff: orderForm.responsible_staff || null,
      note: orderForm.note || null
    });
    await refreshOne(orderingRequest.value.id);
    closeOrderForm();
  } catch (error) {
    alert(error.response?.data?.detail || '登記叫貨失敗');
  } finally {
    saving.value = false;
  }
};

const openReceiveForm = async (request) => {
  receivingRequest.value = request;
  const remaining = Math.max(1, (request.requested_quantity || 0) - (request.arrived_quantity || 0));
  receiveForm.quantity = remaining;
  receiveForm.is_substitution = false;
  receiveForm.received_product_id = request.product_id;
  receiveForm.replace_work_order_line_item = false;
  receiveForm.replacement_unit_price = request.product?.price || 0;
  receiveForm.substitution_reason = '';
  receiveForm.actor = adminUser.value?.full_name || adminUser.value?.username || '';
  receiveForm.note = '';
  try {
    inventoryItems.value = await getInventoryItems({ type: 'all' });
  } catch (error) {
    receivingRequest.value = null;
    alert(error.response?.data?.detail || '載入庫存品項失敗');
  }
};

const setReceiveMode = (isSubstitution) => {
  receiveForm.is_substitution = isSubstitution;
  receiveForm.received_product_id = isSubstitution ? null : receivingRequest.value?.product_id;
  receiveForm.replace_work_order_line_item = isSubstitution && Boolean(receivingRequest.value?.work_order_line_item_id);
  receiveForm.substitution_reason = '';
  receiveForm.replacement_unit_price = 0;
};

watch(
  () => receiveForm.received_product_id,
  productId => {
    if (!receiveForm.is_substitution) return;
    const product = inventoryItems.value.find(item => item.id === productId);
    if (product) receiveForm.replacement_unit_price = Number(product.price || 0);
  }
);

const closeReceiveForm = () => {
  receivingRequest.value = null;
};

const submitReceive = async () => {
  if (!receivingRequest.value) return;
  saving.value = true;
  try {
    await receivePurchaseRequest(receivingRequest.value.id, {
      quantity: receiveForm.quantity,
      received_product_id: receiveForm.is_substitution ? receiveForm.received_product_id : null,
      replace_work_order_line_item: receiveForm.is_substitution && receiveForm.replace_work_order_line_item,
      replacement_unit_price: receiveForm.replace_work_order_line_item ? receiveForm.replacement_unit_price : null,
      substitution_reason: receiveForm.is_substitution ? receiveForm.substitution_reason : null,
      actor: receiveForm.actor || null,
      note: receiveForm.note || null
    });
    await refreshOne(receivingRequest.value.id);
    closeReceiveForm();
  } catch (error) {
    alert(error.response?.data?.detail || '登記到貨失敗');
  } finally {
    saving.value = false;
  }
};

const cancelRequest = async (request) => {
  if (!window.confirm(`確定取消「${request.item_name}」的叫貨需求？`)) return;
  try {
    await cancelPurchaseRequest(request.id, {});
    await refreshOne(request.id);
  } catch (error) {
    alert(error.response?.data?.detail || '取消叫貨需求失敗');
  }
};

const submitAssign = async () => {
  if (!selectedRequest.value) return;
  saving.value = true;
  try {
    await assignPurchaseRequest(selectedRequest.value.id, {
      work_order_id: assignForm.work_order_id,
      work_order_line_item_id: assignForm.work_order_line_item_id,
      quantity: assignForm.quantity,
      note: assignForm.note || null
    });
    await refreshOne(selectedRequest.value.id);
  } catch (error) {
    alert(error.response?.data?.detail || '分配到工單失敗');
  } finally {
    saving.value = false;
  }
};

watch(
  () => route.query.status,
  (status) => {
    if (status && tabStatusMap[status]) activeTab.value = status;
  }
);

onMounted(fetchRequests);
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-purchases {
  color: $text-primary;
}

.section-header,
.header-actions,
.tabs,
.modal-header,
.form-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.section-header {
  margin-bottom: 1.4rem;

  h2 {
    color: $primary-light;
    margin: 0 0 0.35rem;
  }

  p {
    color: $text-secondary;
    margin: 0;
  }
}

.tabs {
  justify-content: flex-start;
  flex-wrap: wrap;
  margin-bottom: 1rem;

  button {
    border: 1px solid rgba($primary-light, 0.35);
    border-radius: 6px;
    padding: 0.65rem 0.95rem;
    color: $text-primary;
    background: rgba($background-color, 0.72);
    cursor: pointer;

    &.active {
      color: $background-color;
      background: $primary-light;
    }

    span {
      margin-left: 0.45rem;
      font-weight: 700;
    }
  }
}

.table-wrap {
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  overflow: auto;
  background-color: $dark-grey;
}

.purchase-table,
.mini-table {
  width: 100%;
  border-collapse: collapse;

  th,
  td {
    border-bottom: 1px solid rgba($medium-grey, 0.9);
    padding: 0.85rem 1rem;
    text-align: left;
    vertical-align: middle;
    white-space: nowrap;
  }

  th {
    color: $text-secondary;
    background: rgba($background-color, 0.78);
    font-weight: 700;
  }

  strong,
  small {
    display: block;
  }

  small {
    color: $text-secondary;
    margin-top: 0.25rem;
  }
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.btn {
  border: 1px solid rgba($primary-light, 0.35);
  border-radius: 6px;
  padding: 0.55rem 0.8rem;
  color: $text-primary;
  background: rgba($background-color, 0.72);
  cursor: pointer;

  &.btn-primary {
    color: $background-color;
    background: $primary-light;
  }

  &.btn-outline {
    background: transparent;
  }

  &.text {
    border-color: transparent;
    padding: 0.35rem 0.45rem;
    color: $primary-light;
    background: transparent;
  }

  &.danger {
    color: #ff6b6b;
  }
}

.status-tag {
  display: inline-flex;
  border-radius: 999px;
  padding: 0.25rem 0.55rem;
  color: $text-primary;
  background: rgba($medium-grey, 0.35);

  &.PENDING_ORDER,
  &.ORDERED,
  &.PARTIAL_ARRIVED,
  &.ARRIVED_PENDING_ASSIGNMENT {
    color: #facc15;
    background: rgba(#facc15, 0.16);
  }

  &.ASSIGNED_TO_WORK_ORDER,
  &.COMPLETED {
    color: #86efac;
    background: rgba(#86efac, 0.14);
  }

  &.CANCELED {
    color: #fca5a5;
    background: rgba(#fca5a5, 0.14);
  }
}

.receive-mode {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-bottom: 1rem;

  button {
    border: 1px solid $medium-grey;
    padding: 0.65rem;
    color: $text-primary;
    background: $background-color;
    cursor: pointer;

    &.active {
      border-color: $primary-light;
      color: $background-color;
      background: $primary-light;
    }
  }
}

.check-row {
  flex-direction: row !important;
  align-items: center;

  input {
    width: 18px;
    height: 18px;
  }
}

.muted-hint {
  color: $text-secondary;
  font-size: 0.86rem;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(#000, 0.68);
}

.modal-content {
  width: min(980px, 96vw);
  max-height: 90vh;
  overflow: auto;
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  padding: 1.25rem;
  background: $dark-grey;

  &.small {
    width: min(520px, 96vw);
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin-bottom: 0.85rem;
    color: $text-secondary;
  }
}

.modal-header {
  margin-bottom: 1rem;

  h3,
  p {
    margin: 0;
  }

  p {
    color: $text-secondary;
    margin-top: 0.25rem;
  }
}

.icon-btn {
  border: 0;
  color: $text-primary;
  background: transparent;
  cursor: pointer;
  font-size: 1.4rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.detail-panel {
  border: 1px solid rgba($medium-grey, 0.8);
  border-radius: $border-radius;
  padding: 1rem;
  margin-bottom: 1rem;
  background: rgba($background-color, 0.4);

  h4 {
    margin: 0 0 0.85rem;
  }

  dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.7rem;
    margin: 0;
  }

  dt {
    color: $text-secondary;
    font-size: 0.85rem;
  }

  dd {
    margin: 0.15rem 0 0;
  }
}

.assign-form {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr)) auto;
  gap: 0.75rem;
  align-items: end;
  margin-bottom: 1rem;

  label {
    margin: 0;
  }
}

input,
select,
textarea {
  border: 1px solid $medium-grey;
  border-radius: 6px;
  padding: 0.65rem 0.75rem;
  color: $text-primary;
  background: $background-color;
}

.loading,
.empty-state,
.muted-line {
  padding: 2.5rem;
  text-align: center;
  color: $text-disabled;
}

@media (max-width: 760px) {
  .section-header,
  .header-actions,
  .form-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .detail-grid,
  .detail-panel dl,
  .assign-form {
    grid-template-columns: 1fr;
  }
}
</style>
