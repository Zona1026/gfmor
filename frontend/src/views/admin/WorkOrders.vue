<template>
  <div class="admin-work-orders">
    <div class="section-header">
      <div>
        <h2>工單管理</h2>
        <p>以車牌快速找單，並管理報價、施工、收款與主管審核。</p>
      </div>
      <button class="btn btn-primary" @click="openCreateModal">新增工單</button>
    </div>

    <div class="quick-tabs">
      <button
        v-for="option in filterOptions"
        :key="option.value"
        class="filter-btn"
        :class="{ active: activeFilter === option.value || (option.value === 'all' && !activeFilter) }"
        @click="setFilter(option.value)"
      >
        {{ option.label }}
      </button>
    </div>

    <div class="toolbar">
      <div class="search-box">
        <input
          v-model.trim="searchKeyword"
          type="search"
          placeholder="搜尋車牌、客戶、電話、預約單號或工單號"
          @keyup.enter="applyFilters"
        />
        <button class="btn btn-primary" @click="applyFilters">搜尋</button>
      </div>
      <input v-model="filterDate" type="date" class="date-picker" @change="applyFilters" />
      <button class="btn btn-outline" @click="showTodayWorkOrders">今日工單</button>
      <button class="btn btn-ghost" @click="clearFilters">清除</button>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else class="table-wrap">
      <table v-if="workOrders.length" class="work-order-table">
        <thead>
          <tr>
            <th>工單</th>
            <th>客戶</th>
            <th>車輛 / 設備</th>
            <th>服務類型</th>
            <th>工單狀態</th>
            <th>付款狀態</th>
            <th>負責人</th>
            <th>預約時間</th>
            <th>總金額</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="workOrder in workOrders" :key="workOrder.id" @click="openDetail(workOrder.id)">
            <td class="strong-cell">#{{ workOrder.id }}</td>
            <td>
              <strong>{{ workOrder.customer_name || workOrder.booking?.user?.name || '-' }}</strong>
              <span class="secondary-line">{{ workOrder.customer_phone || workOrder.booking?.user?.phone || '-' }}</span>
            </td>
            <td class="strong-cell">
              {{ workOrder.vehicle_license_plate || workOrder.booking?.motor?.license_plate || '-' }}
              <span class="secondary-line">{{ workOrder.vehicle_model || workOrder.booking?.motor?.model_name || '-' }}</span>
            </td>
            <td>{{ serviceTypeMap[workOrder.service_type] || workOrder.service_type }}</td>
            <td>
              <span class="status-tag" :class="workOrder.status">
                {{ statusMap[workOrder.status] || workOrder.status }}
              </span>
            </td>
            <td>
              <span class="payment-tag" :class="workOrder.payment_status">
                {{ paymentStatusMap[workOrder.payment_status] || workOrder.payment_status }}
              </span>
            </td>
            <td>{{ workOrder.responsible_staff || '-' }}</td>
            <td>{{ formatDateTime(workOrder.scheduled_at || workOrder.booking?.booking_time) }}</td>
            <td class="amount">NT$ {{ workOrder.total_amount?.toLocaleString() || 0 }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">目前沒有符合條件的工單。</div>
    </div>

    <div v-if="showCreateModal" class="modal-overlay" @click.self="closeCreateModal">
      <div class="modal-content large">
        <div class="modal-header">
          <h3>新增工單</h3>
          <button class="icon-btn" @click="closeCreateModal">×</button>
        </div>

        <form class="work-order-form" @submit.prevent="submitCreateWorkOrder">
          <section class="form-section">
            <h4>客戶來源</h4>
            <div class="segmented">
              <button type="button" :class="{ active: createSource === 'member' }" @click="createSource = 'member'">會員</button>
              <button type="button" :class="{ active: createSource === 'guest' }" @click="createSource = 'guest'">散客</button>
            </div>

            <div v-if="createSource === 'member'" class="source-grid">
              <div class="form-row search-row">
                <input v-model.trim="memberSearch" placeholder="輸入會員姓名搜尋" @keyup.enter.prevent="handleMemberSearch" />
                <button type="button" class="btn btn-outline" @click="handleMemberSearch">搜尋會員</button>
              </div>
              <label>
                會員車輛
                <select v-model="selectedMemberMotorKey" @change="applySelectedMemberMotor">
                  <option value="">請選擇會員車輛</option>
                  <option v-for="option in memberMotorOptions" :key="option.key" :value="option.key">
                    {{ option.user.name }} / {{ option.motor.license_plate }} / {{ option.motor.model_name || '未填車型' }}
                  </option>
                </select>
              </label>
            </div>

            <div v-else class="source-grid">
              <div class="form-row search-row">
                <input v-model.trim="guestSearch" placeholder="輸入散客姓名或電話搜尋" @keyup.enter.prevent="handleGuestSearch" />
                <button type="button" class="btn btn-outline" @click="handleGuestSearch">搜尋散客</button>
              </div>
              <div v-if="guestResults.length" class="result-list">
                <button
                  v-for="guest in guestResults"
                  :key="guest.id"
                  type="button"
                  @click="selectGuest(guest)"
                >
                  {{ guest.name }} / {{ guest.phone }}
                </button>
              </div>
              <div class="form-grid">
                <label>
                  散客姓名
                  <input v-model.trim="createForm.guest_name" required />
                </label>
                <label>
                  散客電話
                  <input v-model.trim="createForm.guest_phone" required />
                </label>
              </div>
            </div>
          </section>

          <section class="form-section">
            <h4>基本資料</h4>
            <div class="form-grid">
              <label>
                車牌
                <input v-model.trim="createForm.vehicle_license_plate" required />
              </label>
              <label>
                品牌
                <input v-model.trim="createForm.vehicle_brand" />
              </label>
              <label>
                車型
                <input v-model.trim="createForm.vehicle_model" required />
              </label>
              <label>
                里程
                <input v-model.number="createForm.vehicle_mileage" type="number" min="0" required />
              </label>
              <label>
                服務類型
                <select v-model="createForm.service_type">
                  <option v-for="(label, value) in serviceTypeMap" :key="value" :value="value">{{ label }}</option>
                </select>
              </label>
              <label>
                負責人
                <input v-model.trim="createForm.responsible_staff" required />
              </label>
              <label>
                預約時間
                <input v-model="createForm.scheduled_at" type="datetime-local" />
              </label>
            </div>
            <label>
              問題描述
              <textarea v-model.trim="createForm.problem_description" rows="3"></textarea>
            </label>
            <label>
              備註
              <textarea v-model.trim="createForm.notes" rows="2"></textarea>
            </label>
          </section>

          <section class="form-section">
            <div class="section-title-row">
              <h4>工單明細</h4>
              <button type="button" class="btn btn-outline" @click="addCreateLineItem">新增明細</button>
            </div>
            <div class="line-editor">
              <div v-for="(item, index) in createLineItems" :key="index" class="line-row">
                <select v-model="item.type" @change="handleLineTypeChange(item)">
                  <option v-for="(label, value) in lineItemTypeMap" :key="value" :value="value">{{ label }}</option>
                </select>
                <select v-if="item.type === 'PART'" v-model.number="item.product_id" @change="applyProductToLine(item)">
                  <option :value="null">選擇商品</option>
                  <option v-for="product in products" :key="product.id" :value="product.id">
                    {{ product.name }} / NT$ {{ product.price }} / 庫存 {{ product.stock }}
                  </option>
                </select>
                <input v-model.trim="item.name" placeholder="明細名稱" />
                <input v-model.number="item.quantity" type="number" min="1" />
                <input v-model.number="item.unit_price" type="number" min="0" />
                <span class="line-total">NT$ {{ lineItemTotal(item).toLocaleString() }}</span>
                <button type="button" class="icon-btn danger" @click="removeCreateLineItem(index)">×</button>
              </div>
            </div>
            <div class="total-row">
              <span>總金額</span>
              <strong>NT$ {{ createTotal.toLocaleString() }}</strong>
            </div>
          </section>

          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="closeCreateModal">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">建立工單</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="selectedWorkOrder" class="modal-overlay" @click.self="closeDetail">
      <div class="modal-content xlarge">
        <div class="modal-header">
          <div>
            <h3>工單 #{{ selectedWorkOrder.id }}</h3>
            <p>{{ selectedWorkOrder.customer_name }} / {{ selectedWorkOrder.vehicle_license_plate }}</p>
          </div>
          <div class="modal-actions">
            <button
              v-if="canUseCriticalWorkOrder && !selectedWorkOrder.deleted_at"
              class="btn btn-danger"
              type="button"
              @click="deleteSelectedWorkOrder"
            >
              刪除工單
            </button>
            <button class="icon-btn" @click="closeDetail">×</button>
          </div>
        </div>

        <div class="detail-grid">
          <section class="form-section">
            <h4>基本資料</h4>
            <div class="form-grid">
              <label>
                服務類型
                <select v-model="detailForm.service_type">
                  <option v-for="(label, value) in serviceTypeMap" :key="value" :value="value">{{ label }}</option>
                </select>
              </label>
              <label>
                工單狀態
                <select v-model="detailForm.status">
                  <option
                    v-for="(label, value) in statusMap"
                    :key="value"
                    :value="value"
                    :disabled="isGatedStatus(value) && hasBlockingApproval(selectedWorkOrder, value)"
                  >
                    {{ label }}
                  </option>
                </select>
              </label>
              <label>
                負責人
                <input v-model.trim="detailForm.responsible_staff" />
              </label>
              <label>
                預約時間
                <input v-model="detailForm.scheduled_at" type="datetime-local" />
              </label>
            </div>
            <label>
              問題描述
              <textarea v-model.trim="detailForm.problem_description" rows="3"></textarea>
            </label>
            <label>
              檢查結果
              <textarea v-model.trim="detailForm.inspection_result" rows="3"></textarea>
            </label>
            <label>
              備註
              <textarea v-model.trim="detailForm.notes" rows="2"></textarea>
            </label>
            <div v-if="hasBlockingApproval(selectedWorkOrder)" class="warning-text">
              此工單仍有待主管審核或退回項目，不能進入施工中、待收款或已完工。
            </div>
            <div class="form-actions">
              <button class="btn btn-primary" @click="saveDetail" :disabled="saving || !canEditWorkOrder">儲存資料</button>
            </div>
          </section>

          <section class="form-section">
            <h4>金額與付款</h4>
            <dl class="money-summary">
              <div><dt>總金額</dt><dd>NT$ {{ selectedWorkOrder.total_amount?.toLocaleString() || 0 }}</dd></div>
              <div><dt>已收款</dt><dd>NT$ {{ selectedWorkOrder.paid_amount?.toLocaleString() || 0 }}</dd></div>
              <div><dt>待收款</dt><dd>NT$ {{ selectedWorkOrder.balance_amount?.toLocaleString() || 0 }}</dd></div>
              <div><dt>付款狀態</dt><dd>{{ paymentStatusMap[selectedWorkOrder.payment_status] }}</dd></div>
            </dl>
            <div class="payment-form">
              <input v-model.number="paymentForm.amount" type="number" min="1" placeholder="付款金額" />
              <input v-model.trim="paymentForm.method" placeholder="付款方式" />
              <button class="btn btn-outline" @click="submitPayment">登錄付款</button>
            </div>
            <table v-if="selectedWorkOrder.payments?.length" class="mini-table">
              <thead>
                <tr><th>時間</th><th>方式</th><th>金額</th></tr>
              </thead>
              <tbody>
                <tr v-for="payment in selectedWorkOrder.payments" :key="payment.id">
                  <td>{{ formatDateTime(payment.paid_at) }}</td>
                  <td>{{ payment.method || '-' }}</td>
                  <td>NT$ {{ payment.amount?.toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
          </section>
        </div>

        <section class="form-section">
          <div class="section-title-row">
            <h4>施工 / 零件 / 工資 / 折扣明細</h4>
            <button type="button" class="btn btn-outline" :disabled="!canEditWorkOrder" @click="addDetailLineItem">新增明細</button>
          </div>
          <div class="line-editor">
            <div v-for="(item, index) in detailLineItems" :key="item.id || index" class="line-row">
              <select v-model="item.type" :disabled="isLineItemInventoryLocked(item)">
                <option v-for="(label, value) in lineItemTypeMap" :key="value" :value="value">{{ label }}</option>
              </select>
              <select v-if="item.type === 'PART'" v-model.number="item.product_id" :disabled="isLineItemInventoryLocked(item)" @change="applyProductToLine(item)">
                <option :value="null">選擇商品</option>
                <option v-for="product in products" :key="product.id" :value="product.id">
                  {{ product.name }} / NT$ {{ product.price }} / 庫存 {{ product.stock }}
                </option>
              </select>
              <input v-model.trim="item.name" :disabled="isLineItemInventoryLocked(item)" placeholder="明細名稱" />
              <input v-model.number="item.quantity" type="number" min="1" :disabled="isLineItemInventoryLocked(item)" />
              <input v-model.number="item.unit_price" type="number" min="0" :disabled="isLineItemInventoryLocked(item)" />
              <span class="line-total">
                NT$ {{ lineItemTotal(item).toLocaleString() }}
                <small v-if="item.type === 'PART'">{{ inventoryStatusText(item) }}</small>
              </span>
              <button type="button" class="icon-btn danger" :disabled="isLineItemInventoryLocked(item)" @click="removeDetailLineItem(index)">×</button>
            </div>
          </div>
          <div class="total-row">
            <span>總金額</span>
            <strong>NT$ {{ detailTotal.toLocaleString() }}</strong>
          </div>
          <div class="form-actions">
            <button class="btn btn-primary" @click="saveLineItems" :disabled="saving || !canEditWorkOrder">儲存明細</button>
          </div>
        </section>

        <section class="form-section">
          <h4>主管審核</h4>
          <div v-if="pendingInventoryApprovals.length" class="approval-actions">
            <template v-if="canReviewApprovals">
              <button
                v-for="approval in pendingInventoryApprovals"
                :key="approval.id"
                class="btn btn-primary"
                @click="reviewDetailApproval(approval.id, true)"
              >
                {{ inventoryApprovalActionLabel(approval.type) }}
              </button>
              <button
                v-for="approval in pendingInventoryApprovals"
                :key="`reject-${approval.id}`"
                class="btn btn-danger"
                @click="reviewDetailApproval(approval.id, false)"
              >
                退回{{ approvalTypeMap[approval.type] || '' }}
              </button>
            </template>
            <span v-else class="warning-text">此工單有庫存確認項目，僅最高級可處理。</span>
          </div>
          <table v-if="selectedWorkOrder.approvals?.length" class="mini-table">
            <thead>
              <tr><th>類型</th><th>原因</th><th>狀態</th><th>建立時間</th></tr>
            </thead>
            <tbody>
              <tr v-for="approval in selectedWorkOrder.approvals" :key="approval.id">
                <td>{{ approvalTypeMap[approval.type] || approval.type }}</td>
                <td>{{ approval.reason || approval.title }}</td>
                <td>{{ approvalStatusMap[approval.status] || approval.status }}</td>
                <td>{{ formatDateTime(approval.requested_at) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="muted-line">目前沒有主管審核項目。</div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useRoute, useRouter } from 'vue-router';
import {
  addWorkOrderPayment,
  approveWorkOrderApproval,
  createWorkOrder,
  deleteWorkOrder,
  getGuestCustomers,
  getProducts,
  getWorkOrder,
  getWorkOrders,
  rejectWorkOrderApproval,
  searchUsersByName,
  updateWorkOrder
} from '../../api/admin';
import { useAuthStore } from '../../store/auth';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const { adminUser } = storeToRefs(authStore);

const loading = ref(false);
const saving = ref(false);
const workOrders = ref([]);
const products = ref([]);
const activeFilter = ref('');
const searchKeyword = ref('');
const filterDate = ref('');
const managerRoles = ['最高級', '管理層'];
const canEditWorkOrder = computed(() => managerRoles.includes(adminUser.value?.role));
const canUseCriticalWorkOrder = computed(() => adminUser.value?.role === '最高級');
const canReviewApprovals = computed(() => canUseCriticalWorkOrder.value);

const showCreateModal = ref(false);
const createSource = ref('guest');
const memberSearch = ref('');
const memberResults = ref([]);
const selectedMemberMotorKey = ref('');
const guestSearch = ref('');
const guestResults = ref([]);
const createForm = ref(defaultCreateForm());
const createLineItems = ref([defaultLineItem()]);

const selectedWorkOrder = ref(null);
const detailForm = ref({});
const detailLineItems = ref([]);
const paymentForm = ref({ amount: null, method: '', note: '' });
const pendingInventoryApprovals = computed(() => {
  return (selectedWorkOrder.value?.approvals || []).filter(approval => {
    return approval.status === 'PENDING' && [
      'INVENTORY_RESERVATION',
      'INVENTORY_CONSUMPTION'
    ].includes(approval.type);
  });
});

const serviceTypeMap = {
  REPAIR: '維修',
  MAINTENANCE: '保養',
  MODIFICATION: '改裝'
};

const statusMap = {
  PENDING: '待檢查',
  INSPECTION_PENDING: '待檢查',
  QUOTE_PENDING: '待報價',
  CUSTOMER_CONFIRMATION_PENDING: '等待客戶確認',
  SUPERVISOR_APPROVAL_PENDING: '待主管確認',
  IN_PROGRESS: '施工中',
  AWAITING_PAYMENT: '待收款',
  COMPLETED: '已完工',
  CANCELED: '已取消'
};

const paymentStatusMap = {
  UNPAID: '未付款',
  PARTIALLY_PAID: '部分付款',
  PAID: '已付款',
  REFUNDED: '已退款'
};

const lineItemTypeMap = {
  SERVICE: '施工項目',
  PART: '零件 / 耗材',
  LABOR: '工資 / 服務費',
  DISCOUNT: '折扣'
};

const approvalTypeMap = {
  DISCOUNT: '折扣',
  HIGH_QUOTE: '高額報價',
  STATUS_CHANGE: '狀態變更',
  INVENTORY_RESERVATION: '確認預留',
  INVENTORY_CONSUMPTION: '確認扣庫存'
};

const approvalStatusMap = {
  PENDING: '待審核',
  APPROVED: '已核准',
  REJECTED: '已退回'
};

const filterOptions = [
  { label: '全部工單', value: 'all' },
  { label: '維修工單', value: 'service:REPAIR' },
  { label: '保養工單', value: 'service:MAINTENANCE' },
  { label: '改裝工單', value: 'service:MODIFICATION' },
  { label: '待檢查', value: 'status:INSPECTION_PENDING' },
  { label: '待報價', value: 'status:QUOTE_PENDING' },
  { label: '施工中', value: 'status:IN_PROGRESS' },
  { label: '待收款', value: 'status:AWAITING_PAYMENT' },
  { label: '已完工', value: 'status:COMPLETED' }
];

const gatedStatuses = ['IN_PROGRESS', 'AWAITING_PAYMENT', 'COMPLETED'];

const memberMotorOptions = computed(() => {
  const options = [];
  for (const user of memberResults.value) {
    for (const motor of user.motors || []) {
      options.push({
        key: `${user.google_id}::${motor.id}`,
        user,
        motor
      });
    }
  }
  return options;
});

const createTotal = computed(() => calculateTotal(createLineItems.value));
const detailTotal = computed(() => calculateTotal(detailLineItems.value));

function defaultCreateForm() {
  return {
    google_id: '',
    guest_customer_id: null,
    guest_name: '',
    guest_phone: '',
    motor_id: null,
    vehicle_license_plate: '',
    vehicle_brand: '',
    vehicle_model: '',
    vehicle_vin: '',
    vehicle_mileage: null,
    service_type: 'MAINTENANCE',
    problem_description: '',
    responsible_staff: '',
    scheduled_at: '',
    notes: ''
  };
}

function defaultLineItem() {
  return {
    type: 'SERVICE',
    name: '',
    description: '',
    product_id: null,
    quantity: 1,
    unit_price: 0,
    is_confirmed: 1
  };
}

const readQuery = () => {
  searchKeyword.value = typeof route.query.q === 'string' ? route.query.q : '';
  filterDate.value = typeof route.query.date === 'string' ? route.query.date : '';
  if (typeof route.query.status === 'string') {
    activeFilter.value = route.query.status === 'active' ? 'active' : `status:${route.query.status}`;
  } else {
    activeFilter.value = typeof route.query.view === 'string' ? route.query.view : '';
  }
};

const buildQuery = () => {
  const query = {};
  if (activeFilter.value && activeFilter.value !== 'active') query.view = activeFilter.value;
  if (searchKeyword.value) query.q = searchKeyword.value;
  if (filterDate.value) query.date = filterDate.value;
  return query;
};

const filterToParams = () => {
  const params = { skip: 0, limit: 200 };
  if (activeFilter.value === 'active') {
    params.status = 'active';
  } else if (activeFilter.value?.startsWith('status:')) {
    params.status = activeFilter.value.split(':')[1];
  } else if (activeFilter.value?.startsWith('service:')) {
    params.service_type = activeFilter.value.split(':')[1];
  }
  if (searchKeyword.value) params.q = searchKeyword.value;
  if (filterDate.value) params.date_str = filterDate.value;
  return params;
};

const applyFilters = async () => {
  await router.replace({ path: route.path, query: buildQuery() });
  await fetchWorkOrders();
};

const setFilter = (value) => {
  activeFilter.value = value === 'all' ? '' : value;
  applyFilters();
};

const showTodayWorkOrders = () => {
  filterDate.value = new Date().toLocaleDateString('en-CA');
  applyFilters();
};

const clearFilters = () => {
  activeFilter.value = '';
  searchKeyword.value = '';
  filterDate.value = '';
  applyFilters();
};

const fetchWorkOrders = async () => {
  loading.value = true;
  try {
    workOrders.value = await getWorkOrders(filterToParams());
  } catch (error) {
    console.error('載入工單失敗:', error);
    workOrders.value = [];
  } finally {
    loading.value = false;
  }
};

const fetchProducts = async () => {
  try {
    products.value = await getProducts();
  } catch (error) {
    console.error('載入商品失敗:', error);
  }
};

const openCreateModal = () => {
  showCreateModal.value = true;
  fetchProducts();
};

const closeCreateModal = () => {
  showCreateModal.value = false;
  createSource.value = 'guest';
  createForm.value = defaultCreateForm();
  createLineItems.value = [defaultLineItem()];
  selectedMemberMotorKey.value = '';
  memberResults.value = [];
  guestResults.value = [];
};

const handleMemberSearch = async () => {
  if (!memberSearch.value) return;
  memberResults.value = await searchUsersByName(memberSearch.value);
};

const handleGuestSearch = async () => {
  guestResults.value = await getGuestCustomers(guestSearch.value);
};

const selectGuest = (guest) => {
  createForm.value.guest_customer_id = guest.id;
  createForm.value.guest_name = guest.name;
  createForm.value.guest_phone = guest.phone;
};

const applySelectedMemberMotor = () => {
  const selected = memberMotorOptions.value.find(option => option.key === selectedMemberMotorKey.value);
  if (!selected) return;
  createForm.value.google_id = selected.user.google_id;
  createForm.value.motor_id = selected.motor.id;
  createForm.value.vehicle_license_plate = selected.motor.license_plate || '';
  createForm.value.vehicle_brand = selected.motor.brand || '';
  createForm.value.vehicle_model = selected.motor.model_name || '';
  createForm.value.vehicle_vin = selected.motor.vin || '';
  createForm.value.vehicle_mileage = selected.motor.mileage ?? null;
};

const addCreateLineItem = () => {
  createLineItems.value.push(defaultLineItem());
};

const removeCreateLineItem = (index) => {
  createLineItems.value.splice(index, 1);
};

const addDetailLineItem = () => {
  detailLineItems.value.push(defaultLineItem());
};

const removeDetailLineItem = (index) => {
  detailLineItems.value.splice(index, 1);
};

const handleLineTypeChange = (item) => {
  if (item.type !== 'PART') item.product_id = null;
};

const applyProductToLine = (item) => {
  const product = products.value.find(product => product.id === Number(item.product_id));
  if (!product) return;
  item.name = product.name;
  item.unit_price = product.price;
};

const lineItemTotal = (item) => {
  return Math.max(0, Number(item.quantity) || 0) * Math.max(0, Number(item.unit_price) || 0);
};

const isLineItemInventoryLocked = (item) => {
  return Boolean(item.inventory_deducted)
    || Number(item.inventory_consumed_quantity || 0) > 0
    || Number(item.inventory_reserved_quantity || 0) > 0;
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

const calculateTotal = (items) => {
  let subtotal = 0;
  let discount = 0;
  for (const item of items) {
    const amount = lineItemTotal(item);
    if (item.type === 'DISCOUNT') discount += amount;
    else subtotal += amount;
  }
  return Math.max(0, subtotal - discount);
};

const cleanLineItem = (item) => ({
  type: item.type,
  name: item.name || (item.type === 'DISCOUNT' ? '折扣' : ''),
  description: item.description || '',
  product_id: item.type === 'PART' ? Number(item.product_id) || null : null,
  quantity: Number(item.quantity) || 1,
  unit_price: Number(item.unit_price) || 0,
  is_confirmed: Number(item.is_confirmed ?? 1)
});

const hasText = (value) => String(value ?? '').trim().length > 0;

const hasMileageValue = (value) => {
  if (value === null || value === undefined || value === '') return false;
  const mileage = Number(value);
  return Number.isFinite(mileage) && mileage >= 0;
};

const validateCreateRequiredFields = () => {
  if (!hasText(createForm.value.vehicle_license_plate)) return '車牌為必填';
  if (!hasText(createForm.value.vehicle_model)) return '車型為必填';
  if (!hasMileageValue(createForm.value.vehicle_mileage)) return '里程為必填';
  if (!hasText(createForm.value.responsible_staff)) return '負責人為必填';
  return '';
};

const submitCreateWorkOrder = async () => {
  const validationMessage = validateCreateRequiredFields();
  if (validationMessage) {
    alert(validationMessage);
    return;
  }

  saving.value = true;
  try {
    const payload = {
      ...createForm.value,
      vehicle_mileage: Number(createForm.value.vehicle_mileage),
      scheduled_at: createForm.value.scheduled_at || null,
      line_items: createLineItems.value.filter(item => item.name || item.product_id).map(cleanLineItem)
    };
    if (createSource.value === 'guest') {
      delete payload.google_id;
      delete payload.motor_id;
    } else {
      delete payload.guest_customer_id;
      delete payload.guest_name;
      delete payload.guest_phone;
    }
    const created = await createWorkOrder(payload);
    closeCreateModal();
    await fetchWorkOrders();
    await openDetail(created.id);
  } catch (error) {
    alert(`建立工單失敗：${getErrorMessage(error)}`);
  } finally {
    saving.value = false;
  }
};

const openDetail = async (id) => {
  await fetchProducts();
  selectedWorkOrder.value = await getWorkOrder(id);
  detailForm.value = {
    service_type: selectedWorkOrder.value.service_type,
    status: selectedWorkOrder.value.status,
    problem_description: selectedWorkOrder.value.problem_description || '',
    inspection_result: selectedWorkOrder.value.inspection_result || '',
    responsible_staff: selectedWorkOrder.value.responsible_staff || '',
    scheduled_at: toDatetimeLocal(selectedWorkOrder.value.scheduled_at),
    notes: selectedWorkOrder.value.notes || ''
  };
  detailLineItems.value = (selectedWorkOrder.value.line_items || []).map(item => ({ ...item }));
  paymentForm.value = { amount: selectedWorkOrder.value.balance_amount || null, method: '', note: '' };
};

const closeDetail = () => {
  selectedWorkOrder.value = null;
};

const saveDetail = async () => {
  if (!selectedWorkOrder.value) return;
  saving.value = true;
  try {
    selectedWorkOrder.value = await updateWorkOrder(selectedWorkOrder.value.id, {
      ...detailForm.value,
      scheduled_at: detailForm.value.scheduled_at || null
    });
    await fetchWorkOrders();
    alert('工單資料已儲存');
  } catch (error) {
    alert(`儲存失敗：${getErrorMessage(error)}`);
  } finally {
    saving.value = false;
  }
};

const saveLineItems = async () => {
  if (!selectedWorkOrder.value) return;
  saving.value = true;
  try {
    selectedWorkOrder.value = await updateWorkOrder(selectedWorkOrder.value.id, {
      line_items: detailLineItems.value.filter(item => item.name || item.product_id).map(cleanLineItem)
    });
    detailLineItems.value = (selectedWorkOrder.value.line_items || []).map(item => ({ ...item }));
    await fetchWorkOrders();
    alert('工單明細已儲存');
  } catch (error) {
    alert(`明細儲存失敗：${getErrorMessage(error)}`);
  } finally {
    saving.value = false;
  }
};

const submitPayment = async () => {
  if (!selectedWorkOrder.value || !paymentForm.value.amount) return;
  try {
    selectedWorkOrder.value = await addWorkOrderPayment(selectedWorkOrder.value.id, paymentForm.value);
    paymentForm.value = { amount: selectedWorkOrder.value.balance_amount || null, method: '', note: '' };
    await fetchWorkOrders();
  } catch (error) {
    alert(`付款登錄失敗：${getErrorMessage(error)}`);
  }
};

const isGatedStatus = (status) => gatedStatuses.includes(status);
const hasBlockingApproval = (workOrder, targetStatus = null) => {
  const pending = (workOrder.approvals || []).filter(approval => approval.status === 'PENDING');
  if (targetStatus === 'AWAITING_PAYMENT') {
    return pending.some(approval => approval.type !== 'INVENTORY_CONSUMPTION');
  }
  return pending.length > 0;
};

const inventoryApprovalActionLabel = (type) => {
  if (type === 'INVENTORY_RESERVATION') return '確認預留';
  if (type === 'INVENTORY_CONSUMPTION') return '確認扣庫存';
  return '核准';
};

const reviewDetailApproval = async (id, approved) => {
  if (!selectedWorkOrder.value) return;
  try {
    const payload = { reviewed_by: adminUser.value?.username || adminUser.value?.full_name || '主管' };
    if (approved) await approveWorkOrderApproval(id, payload);
    else await rejectWorkOrderApproval(id, payload);
    selectedWorkOrder.value = await getWorkOrder(selectedWorkOrder.value.id);
    detailLineItems.value = (selectedWorkOrder.value.line_items || []).map(item => ({ ...item }));
    await fetchWorkOrders();
  } catch (error) {
    alert(`主管確認處理失敗：${getErrorMessage(error)}`);
  }
};

const deleteSelectedWorkOrder = async () => {
  if (!selectedWorkOrder.value) return;
  const reason = window.prompt(`請輸入刪除工單 #${selectedWorkOrder.value.id} 的原因`);
  if (!reason) return;
  if (!window.confirm('確定要刪除這張工單？此動作會保留歷史並標記為已取消。')) return;
  try {
    await deleteWorkOrder(selectedWorkOrder.value.id, {
      reason,
      actor: adminUser.value?.username || adminUser.value?.full_name || '最高級'
    });
    closeDetail();
    await fetchWorkOrders();
  } catch (error) {
    alert(`刪除工單失敗：${getErrorMessage(error)}`);
  }
};

const formatDateTime = (iso) => {
  if (!iso) return '-';
  const date = new Date(iso);
  return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const toDatetimeLocal = (iso) => {
  if (!iso) return '';
  const date = new Date(iso);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}T${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const getErrorMessage = (error) => {
  const detail = error.response?.data?.detail;
  if (!detail) return '未知錯誤';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg).join('\n');
  return JSON.stringify(detail);
};

watch(
  () => route.query,
  () => {
    readQuery();
    fetchWorkOrders();
  },
  { immediate: true }
);
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-work-orders {
  color: $text-primary;

  .section-header,
  .toolbar,
  .quick-tabs,
  .search-box,
  .form-actions,
  .approval-actions,
  .modal-actions,
  .section-title-row,
  .payment-form {
    display: flex;
    gap: 0.7rem;
    flex-wrap: wrap;
  }

  .section-header {
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;

    h2 {
      color: $primary-light;
      margin: 0;
    }

    p {
      color: $text-secondary;
      margin: 0.35rem 0 0;
    }
  }

  .quick-tabs,
  .toolbar {
    margin-bottom: 1rem;
    align-items: center;
  }

  .search-box {
    flex: 1 1 360px;

    input {
      flex: 1;
      min-width: 240px;
    }
  }

  input,
  select,
  textarea,
  .date-picker {
    padding: 0.62rem 0.72rem;
    background-color: $dark-grey;
    color: $text-primary;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    font-family: inherit;

    &:focus {
      outline: none;
      border-color: $primary-light;
    }
  }

  textarea {
    resize: vertical;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.38rem;
    color: $text-secondary;
    font-size: 0.88rem;
  }

  .btn,
  .filter-btn {
    padding: 0.58rem 0.95rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.05);
    color: $text-secondary;
    border-radius: $border-radius;
    cursor: pointer;
    font-weight: 700;
    white-space: nowrap;

    &:disabled {
      cursor: not-allowed;
      opacity: 0.48;
    }
  }

  .filter-btn.active,
  .filter-btn:hover {
    border-color: $primary-color;
    color: $primary-color;
    background: rgba($primary-color, 0.1);
  }

  .btn-primary {
    background-color: $primary-color;
    color: #fff;
    border-color: $primary-color;
  }

  .btn-outline {
    border-color: $medium-grey;
    color: $primary-light;
  }

  .btn-ghost {
    background: transparent;
    color: $text-secondary;
  }

  .icon-btn {
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: $border-radius;
    background: rgba(255, 255, 255, 0.06);
    color: $text-primary;
    cursor: pointer;

    &.danger {
      color: #ff7676;
    }
  }

  .table-wrap {
    background-color: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    overflow: auto;
  }

  .work-order-table,
  .mini-table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      padding: 0.85rem 1rem;
      text-align: left;
      border-bottom: 1px solid $medium-grey;
      white-space: nowrap;
      vertical-align: top;
    }

    th {
      background-color: $background-color;
      color: $text-secondary;
      font-size: 0.86rem;
      font-weight: 600;
    }
  }

  .work-order-table tbody tr {
    cursor: pointer;

    &:hover {
      background-color: rgba($primary-color, 0.06);
    }
  }

  .strong-cell,
  .amount {
    color: $primary-light;
    font-weight: 700;
  }

  .secondary-line,
  .muted-line {
    display: block;
    margin-top: 0.22rem;
    color: $text-secondary;
    font-size: 0.82rem;
    font-weight: 400;
  }

  .status-tag,
  .payment-tag {
    display: inline-flex;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.8rem;
    background-color: rgba($medium-grey, 0.4);
  }

  .INSPECTION_PENDING,
  .PENDING,
  .UNPAID { color: #ffc107; background-color: rgba(#ffc107, 0.15); }
  .QUOTE_PENDING,
  .CUSTOMER_CONFIRMATION_PENDING,
  .PARTIALLY_PAID { color: #ff9800; background-color: rgba(#ff9800, 0.15); }
  .SUPERVISOR_APPROVAL_PENDING { color: #ce93d8; background-color: rgba(#ce93d8, 0.15); }
  .IN_PROGRESS { color: #64b5f6; background-color: rgba(#64b5f6, 0.15); }
  .AWAITING_PAYMENT { color: #ffb74d; background-color: rgba(#ffb74d, 0.15); }
  .COMPLETED,
  .PAID { color: #4caf50; background-color: rgba(#4caf50, 0.15); }
  .CANCELED,
  .REFUNDED { color: #e57373; background-color: rgba(#e57373, 0.15); }

  .loading,
  .empty-state {
    padding: 3rem;
    text-align: center;
    color: $text-disabled;
  }

  .modal-overlay {
    position: fixed;
    inset: 0;
    background-color: rgba(0, 0, 0, 0.72);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    overflow: auto;
    padding: 4vh 1rem;
    z-index: 1000;
  }

  .modal-content {
    width: min(96vw, 920px);
    background-color: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    padding: 1.5rem;
    box-shadow: 0 18px 60px rgba(0, 0, 0, 0.45);

    &.xlarge {
      width: min(98vw, 1180px);
    }
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1rem;

    h3 {
      color: $primary-light;
      margin: 0;
    }

    p {
      color: $text-secondary;
      margin: 0.3rem 0 0;
    }
  }

  .work-order-form,
  .detail-grid {
    display: grid;
    gap: 1rem;
  }

  .detail-grid {
    grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.8fr);
  }

  .form-section {
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    padding: 1rem;
    background-color: $background-color;
    display: grid;
    gap: 0.9rem;

    h4 {
      color: $primary-light;
      margin: 0;
    }
  }

  .form-grid,
  .source-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.8rem;
  }

  .form-row {
    grid-column: 1 / -1;
  }

  .search-row {
    display: flex;
    gap: 0.7rem;

    input {
      flex: 1;
    }
  }

  .segmented {
    display: inline-flex;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    overflow: hidden;
    width: fit-content;

    button {
      border: none;
      padding: 0.55rem 1rem;
      background: transparent;
      color: $text-secondary;
      cursor: pointer;

      &.active {
        background: rgba($primary-color, 0.16);
        color: $primary-light;
      }
    }
  }

  .result-list {
    grid-column: 1 / -1;
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;

    button {
      border: 1px solid $medium-grey;
      background: rgba(255, 255, 255, 0.04);
      color: $text-primary;
      border-radius: $border-radius;
      padding: 0.45rem 0.7rem;
      cursor: pointer;
    }
  }

  .line-editor {
    display: grid;
    gap: 0.55rem;
  }

  .line-row {
    display: grid;
    grid-template-columns: 130px minmax(150px, 1.2fr) minmax(160px, 1.4fr) 88px 110px 110px 36px;
    gap: 0.5rem;
    align-items: center;

    .line-total {
      color: $primary-light;
      font-weight: 700;
      white-space: nowrap;

      small {
        display: block;
        color: $text-secondary;
        font-weight: 400;
      }
    }
  }

  .total-row {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    align-items: center;
    color: $text-secondary;

    strong {
      color: $primary-light;
      font-size: 1.1rem;
    }
  }

  .money-summary {
    display: grid;
    gap: 0.6rem;
    margin: 0;

    div {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
    }

    dt {
      color: $text-secondary;
    }

    dd {
      margin: 0;
      color: $primary-light;
      font-weight: 700;
    }
  }

  .warning-text {
    color: #ffb74d;
    background-color: rgba(#ffb74d, 0.1);
    border: 1px solid rgba(#ffb74d, 0.25);
    border-radius: $border-radius;
    padding: 0.75rem;
  }

  @media (max-width: 980px) {
    .detail-grid,
    .form-grid,
    .source-grid {
      grid-template-columns: 1fr;
    }

    .line-row {
      grid-template-columns: 1fr;
      align-items: stretch;
    }
  }
}
</style>
