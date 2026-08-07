<template>
  <div class="admin-customers">
    <div class="section-header">
      <div>
        <h2>客戶 / 會員管理</h2>
        <p>集中查看客戶資料、車輛、服務紀錄、消費紀錄、備註與會員點數。</p>
      </div>
      <div class="toolbar">
        <input
          v-model.trim="searchKeyword"
          type="text"
          placeholder="搜尋姓名、電話、Email、車牌"
          @keyup.enter="fetchCustomers"
        />
        <select v-model="customerType" @change="fetchCustomers">
          <option value="all">全部客戶</option>
          <option value="member">會員</option>
          <option value="guest">散客</option>
        </select>
        <button class="btn btn-primary" type="button" @click="fetchCustomers">搜尋</button>
      </div>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else class="table-wrap">
      <table class="customers-table">
        <thead>
          <tr>
            <th>類型</th>
            <th>姓名</th>
            <th>電話</th>
            <th>車輛數量</th>
            <th>最近服務</th>
            <th>累積消費</th>
            <th>目前點數</th>
            <th>快到期點數</th>
            <th>備註</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="customer in customers" :key="customerKey(customer)">
            <td>
              <span class="type-tag" :class="customer.customer_type">
                {{ customer.customer_type === 'member' ? '會員' : '散客' }}
              </span>
            </td>
            <td>
              <strong>{{ customer.name }}</strong>
              <span v-if="customer.email" class="secondary-line">{{ customer.email }}</span>
            </td>
            <td>{{ customer.phone || '未填' }}</td>
            <td>{{ formatVehicleCount(customer.vehicle_count) }}</td>
            <td>{{ formatDate(customer.latest_service_at) }}</td>
            <td class="amount">NT$ {{ formatNumber(customer.cumulative_spending) }}</td>
            <td>{{ customer.customer_type === 'member' ? formatNumber(customer.current_points) : '未累積' }}</td>
            <td>{{ customer.customer_type === 'member' ? formatNumber(customer.expiring_soon_points) : '未累積' }}</td>
            <td>
              <span class="note-state" :class="{ active: customer.has_notes }">
                {{ customer.has_notes ? '有' : '無' }}
              </span>
            </td>
            <td>
              <button class="btn btn-sm" type="button" @click="openDetail(customer)">詳情</button>
            </td>
          </tr>
          <tr v-if="customers.length === 0">
            <td colspan="10" class="empty-row">查無符合條件的客戶。</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showDetailModal" class="modal-overlay" @click.self="closeDetail">
      <div class="modal modal-wide">
        <div class="modal-header">
          <div>
            <h3>{{ selectedCustomer?.name }}</h3>
            <p>
              {{ selectedCustomer?.customer_type === 'member' ? '會員' : '散客' }}
              <span v-if="selectedCustomer?.phone"> / {{ selectedCustomer.phone }}</span>
            </p>
          </div>
          <button class="btn btn-outline" type="button" @click="closeDetail">關閉</button>
        </div>

        <div class="tabs">
          <button type="button" :class="{ active: activeTab === 'profile' }" @click="activeTab = 'profile'">客戶資料</button>
          <button type="button" :class="{ active: activeTab === 'vehicles' }" @click="activeTab = 'vehicles'">車輛資料</button>
          <button type="button" :class="{ active: activeTab === 'services' }" @click="activeTab = 'services'">服務紀錄</button>
          <button type="button" :class="{ active: activeTab === 'spending' }" @click="activeTab = 'spending'">消費紀錄</button>
          <button type="button" :class="{ active: activeTab === 'notes' }" @click="activeTab = 'notes'">備註</button>
        </div>

        <div v-if="detailLoading" class="loading detail-loading">載入詳情中...</div>

        <template v-else-if="selectedCustomer">
          <section v-if="activeTab === 'profile'" class="detail-panel">
            <div class="info-grid">
              <div><span>姓名</span><strong>{{ selectedCustomer.name }}</strong></div>
              <div><span>電話</span><strong>{{ selectedCustomer.phone || '未填' }}</strong></div>
              <div><span>Email</span><strong>{{ selectedCustomer.email || '散客未建立 Email' }}</strong></div>
              <div><span>建立 / 加入時間</span><strong>{{ formatDateTime(selectedCustomer.joined_at) }}</strong></div>
              <div><span>車輛數</span><strong>{{ selectedCustomer.vehicle_count }}</strong></div>
              <div><span>累積消費</span><strong>NT$ {{ formatNumber(selectedCustomer.cumulative_spending) }}</strong></div>
              <div><span>目前點數</span><strong>{{ selectedCustomer.customer_type === 'member' ? formatNumber(selectedCustomer.current_points) : '散客未累積' }}</strong></div>
              <div><span>快到期點數</span><strong>{{ selectedCustomer.customer_type === 'member' ? formatNumber(selectedCustomer.expiring_soon_points) : '散客未累積' }}</strong></div>
            </div>
          </section>

          <section v-if="activeTab === 'vehicles'" class="detail-panel">
            <div class="panel-title">
              <h4>車輛資料</h4>
              <span>{{ selectedCustomer.customer_type === 'member' ? '會員車輛沿用既有車籍資料' : '散客車輛會建立在散客車輛主檔' }}</span>
            </div>

            <table v-if="selectedCustomer.vehicles?.length" class="mini-table">
              <thead>
                <tr>
                  <th>車牌</th>
                  <th>廠牌</th>
                  <th>車型</th>
                  <th>里程</th>
                  <th>引擎號碼</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="vehicle in selectedCustomer.vehicles" :key="vehicleKey(vehicle)">
                  <template v-if="editingVehicleKey === vehicleKey(vehicle)">
                    <td><input v-model.trim="vehicleDraft.license_plate" class="inline-input" /></td>
                    <td><input v-model.trim="vehicleDraft.brand" class="inline-input" /></td>
                    <td><input v-model.trim="vehicleDraft.model_name" class="inline-input" /></td>
                    <td><input v-model.number="vehicleDraft.mileage" type="number" class="inline-input" /></td>
                    <td><input v-model.trim="vehicleDraft.vin" class="inline-input" /></td>
                    <td class="action-cell">
                      <button class="btn btn-sm btn-save" type="button" :disabled="savingVehicle" @click="saveVehicle(vehicle)">儲存</button>
                      <button class="btn btn-sm btn-outline" type="button" @click="cancelEditVehicle">取消</button>
                    </td>
                  </template>
                  <template v-else>
                    <td>{{ vehicle.license_plate }}</td>
                    <td>{{ vehicle.brand || '未填' }}</td>
                    <td>{{ vehicle.model_name || '未填' }}</td>
                    <td>{{ vehicle.mileage ? formatNumber(vehicle.mileage) : '未填' }}</td>
                    <td>{{ vehicle.vin || '未填' }}</td>
                    <td><button class="btn btn-sm" type="button" @click="startEditVehicle(vehicle)">編輯</button></td>
                  </template>
                </tr>
              </tbody>
            </table>
            <p v-else class="empty-text">尚未登記車輛。</p>

            <form v-if="selectedCustomer.customer_type === 'guest'" class="guest-motor-form" @submit.prevent="addGuestMotor">
              <h4>新增散客車輛</h4>
              <div class="form-grid">
                <label>車牌<input v-model.trim="newGuestMotor.license_plate" required /></label>
                <label>廠牌<input v-model.trim="newGuestMotor.brand" /></label>
                <label>車型<input v-model.trim="newGuestMotor.model_name" /></label>
                <label>里程<input v-model.number="newGuestMotor.mileage" type="number" /></label>
                <label>引擎號碼<input v-model.trim="newGuestMotor.vin" /></label>
              </div>
              <button class="btn btn-primary" type="submit" :disabled="addingGuestMotor">
                {{ addingGuestMotor ? '新增中...' : '新增車輛' }}
              </button>
            </form>
          </section>

          <section v-if="activeTab === 'services'" class="detail-panel">
            <table v-if="selectedCustomer.service_records?.length" class="mini-table">
              <thead>
                <tr>
                  <th>工單</th>
                  <th>日期</th>
                  <th>服務類型</th>
                  <th>車牌</th>
                  <th>狀態</th>
                  <th>付款</th>
                  <th>負責人</th>
                  <th>金額</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in selectedCustomer.service_records" :key="record.id">
                  <td>#{{ record.work_order_id }}</td>
                  <td>{{ formatDate(record.completed_at || record.scheduled_at || record.created_at) }}</td>
                  <td>{{ serviceTypeMap[record.service_type] || record.service_type }}</td>
                  <td>{{ record.vehicle_license_plate || '未填' }}</td>
                  <td>{{ workOrderStatusMap[record.status] || record.status }}</td>
                  <td>{{ paymentStatusMap[record.payment_status] || record.payment_status }}</td>
                  <td>{{ record.responsible_staff || '未填' }}</td>
                  <td class="amount">NT$ {{ formatNumber(record.total_amount) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="empty-text">尚無服務紀錄。</p>
          </section>

          <section v-if="activeTab === 'spending'" class="detail-panel">
            <table v-if="selectedCustomer.spending_records?.length" class="mini-table">
              <thead>
                <tr>
                  <th>來源</th>
                  <th>日期</th>
                  <th>金額</th>
                  <th>付款方式</th>
                  <th>狀態</th>
                  <th>單號</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in selectedCustomer.spending_records" :key="record.id">
                  <td>{{ spendingSourceMap[record.source] || record.source }}</td>
                  <td>{{ formatDateTime(record.paid_at || record.created_at) }}</td>
                  <td class="amount">NT$ {{ formatNumber(record.amount) }}</td>
                  <td>{{ record.method || '未填' }}</td>
                  <td>{{ orderStatusMap[record.status] || paymentStatusMap[record.status] || record.status }}</td>
                  <td>{{ record.source_label }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="empty-text">尚無消費紀錄。</p>
          </section>

          <section v-if="activeTab === 'notes'" class="detail-panel">
            <p class="text-muted">此備註僅後台可見，不會顯示在客戶端。</p>
            <textarea v-model="detailNotes" rows="7" placeholder="記錄客戶偏好、注意事項、服務提醒..."></textarea>
            <div class="form-actions">
              <button class="btn btn-primary" type="button" :disabled="savingNotes" @click="saveNotes">
                {{ savingNotes ? '儲存中...' : '儲存備註' }}
              </button>
            </div>
          </section>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import {
  createGuestMotor,
  getCustomerDetail,
  getCustomers,
  updateGuestCustomer,
  updateGuestMotor,
  updateMemberNotes
} from '../../api/admin';
import api from '../../api/index';

const loading = ref(false);
const detailLoading = ref(false);
const customers = ref([]);
const searchKeyword = ref('');
const customerType = ref('all');
const showDetailModal = ref(false);
const selectedCustomer = ref(null);
const activeTab = ref('profile');
const detailNotes = ref('');
const savingNotes = ref(false);
const editingVehicleKey = ref('');
const vehicleDraft = ref({});
const savingVehicle = ref(false);
const addingGuestMotor = ref(false);
const newGuestMotor = ref(defaultGuestMotor());

const serviceTypeMap = {
  REPAIR: '維修',
  MAINTENANCE: '保養',
  MODIFICATION: '改裝'
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

const paymentStatusMap = {
  UNPAID: '未付款',
  PARTIALLY_PAID: '部分付款',
  PAID: '已付款',
  REFUNDED: '已退款'
};

const orderStatusMap = {
  PENDING: '待付款',
  DEPOSIT_PAID: '已付訂金',
  FULL_PAID: '已付款',
  COMPLETED: '已完成',
  CANCELED: '已取消'
};

const spendingSourceMap = {
  order: '商城訂單',
  work_order_payment: '工單付款'
};

function defaultGuestMotor() {
  return {
    license_plate: '',
    brand: '',
    model_name: '',
    vin: '',
    mileage: null
  };
}

const customerKey = (customer) => `${customer.customer_type}-${customer.customer_id}`;
const vehicleKey = (vehicle) => `${vehicle.customer_type}-${vehicle.id}`;

const formatNumber = (value) => Number(value || 0).toLocaleString();

const formatVehicleCount = (value) => `${Number(value || 0).toLocaleString()} 台`;

const formatDate = (isoString) => {
  if (!isoString) return '未建立';
  const date = new Date(isoString);
  return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`;
};

const formatDateTime = (isoString) => {
  if (!isoString) return '未建立';
  const date = new Date(isoString);
  return `${formatDate(isoString)} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const getErrorMessage = (error) => {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg).join('、');
  return detail || error?.message || '請稍後再試';
};

const cleanVehiclePayload = (vehicle) => ({
  license_plate: vehicle.license_plate || '',
  brand: vehicle.brand || null,
  model_name: vehicle.model_name || null,
  vin: vehicle.vin || null,
  mileage: vehicle.mileage === '' || vehicle.mileage === null || vehicle.mileage === undefined
    ? null
    : Number(vehicle.mileage)
});

const fetchCustomers = async () => {
  loading.value = true;
  try {
    customers.value = await getCustomers({
      q: searchKeyword.value || undefined,
      type: customerType.value,
      skip: 0,
      limit: 300
    });
  } catch (error) {
    alert(`載入客戶失敗：${getErrorMessage(error)}`);
    customers.value = [];
  } finally {
    loading.value = false;
  }
};

const openDetail = async (customer, tab = 'profile') => {
  showDetailModal.value = true;
  activeTab.value = tab;
  selectedCustomer.value = null;
  await loadCustomerDetail(customer.customer_type, customer.customer_id);
};

const loadCustomerDetail = async (type, id) => {
  detailLoading.value = true;
  try {
    selectedCustomer.value = await getCustomerDetail(type, id);
    detailNotes.value = selectedCustomer.value.notes || '';
  } catch (error) {
    alert(`載入客戶詳情失敗：${getErrorMessage(error)}`);
    closeDetail();
  } finally {
    detailLoading.value = false;
  }
};

const refreshCurrentDetail = async () => {
  if (!selectedCustomer.value) return;
  const { customer_type, customer_id } = selectedCustomer.value;
  await loadCustomerDetail(customer_type, customer_id);
};

const closeDetail = () => {
  showDetailModal.value = false;
  selectedCustomer.value = null;
  activeTab.value = 'profile';
  editingVehicleKey.value = '';
};

const startEditVehicle = (vehicle) => {
  editingVehicleKey.value = vehicleKey(vehicle);
  vehicleDraft.value = { ...vehicle };
};

const cancelEditVehicle = () => {
  editingVehicleKey.value = '';
  vehicleDraft.value = {};
};

const saveVehicle = async (vehicle) => {
  if (!selectedCustomer.value) return;
  const payload = cleanVehiclePayload(vehicleDraft.value);
  if (!payload.license_plate) {
    alert('車牌為必填');
    return;
  }

  savingVehicle.value = true;
  try {
    if (selectedCustomer.value.customer_type === 'member') {
      await api.put(`/motors/${vehicle.id}`, payload);
    } else {
      await updateGuestMotor(selectedCustomer.value.customer_id, vehicle.id, payload);
    }
    cancelEditVehicle();
    await refreshCurrentDetail();
    await fetchCustomers();
  } catch (error) {
    alert(`更新車輛失敗：${getErrorMessage(error)}`);
  } finally {
    savingVehicle.value = false;
  }
};

const addGuestMotor = async () => {
  if (!selectedCustomer.value || selectedCustomer.value.customer_type !== 'guest') return;
  const payload = cleanVehiclePayload(newGuestMotor.value);
  if (!payload.license_plate) {
    alert('車牌為必填');
    return;
  }

  addingGuestMotor.value = true;
  try {
    await createGuestMotor(selectedCustomer.value.customer_id, payload);
    newGuestMotor.value = defaultGuestMotor();
    await refreshCurrentDetail();
    await fetchCustomers();
  } catch (error) {
    alert(`新增散客車輛失敗：${getErrorMessage(error)}`);
  } finally {
    addingGuestMotor.value = false;
  }
};

const saveNotes = async () => {
  if (!selectedCustomer.value) return;
  savingNotes.value = true;
  try {
    if (selectedCustomer.value.customer_type === 'member') {
      await updateMemberNotes(selectedCustomer.value.customer_id, detailNotes.value);
    } else {
      await updateGuestCustomer(selectedCustomer.value.customer_id, { notes: detailNotes.value });
    }
    await refreshCurrentDetail();
    await fetchCustomers();
  } catch (error) {
    alert(`儲存備註失敗：${getErrorMessage(error)}`);
  } finally {
    savingNotes.value = false;
  }
};

onMounted(fetchCustomers);
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-customers {
  color: $text-primary;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;

    h2 {
      color: $primary-light;
      margin: 0 0 0.35rem;
    }

    p {
      margin: 0;
      color: $text-secondary;
      font-size: 0.92rem;
    }
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;

    input,
    select {
      min-height: 40px;
      padding: 0.55rem 0.85rem;
      background-color: $background-color;
      border: 1px solid $medium-grey;
      border-radius: $border-radius;
      color: $text-primary;
      font-size: 0.92rem;

      &:focus {
        outline: none;
        border-color: $primary-color;
      }
    }

    input {
      width: 280px;
    }
  }

  .loading {
    text-align: center;
    padding: 3rem;
    color: $text-secondary;
  }

  .table-wrap {
    overflow-x: auto;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    background-color: $dark-grey;
  }

  .customers-table,
  .mini-table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      padding: 0.8rem 0.9rem;
      text-align: left;
      border-bottom: 1px solid $medium-grey;
      vertical-align: middle;
      white-space: nowrap;
    }

    th {
      background-color: $background-color;
      color: $text-secondary;
      font-size: 0.82rem;
      font-weight: 700;
    }

    tbody tr:hover {
      background-color: rgba($primary-color, 0.05);
    }

    .empty-row {
      text-align: center;
      color: $text-disabled;
      padding: 2rem;
    }
  }

  .secondary-line {
    display: block;
    color: $text-disabled;
    font-size: 0.78rem;
    margin-top: 0.2rem;
  }

  .amount {
    color: $primary-light;
    font-weight: 700;
  }

  .type-tag,
  .note-state {
    display: inline-flex;
    align-items: center;
    min-height: 24px;
    padding: 0 0.55rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    background-color: rgba($medium-grey, 0.45);
    color: $text-secondary;

    &.member {
      color: #64b5f6;
      background-color: rgba(#64b5f6, 0.14);
    }

    &.guest {
      color: #ffb74d;
      background-color: rgba(#ffb74d, 0.14);
    }

    &.active {
      color: #81c784;
      background-color: rgba(#81c784, 0.14);
    }
  }

  .btn {
    min-height: 34px;
    padding: 0.45rem 0.85rem;
    border: 1px solid $primary-color;
    background-color: transparent;
    color: $primary-color;
    border-radius: $border-radius;
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.2s;

    &:hover {
      background-color: $primary-color;
      color: #fff;
    }

    &:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }

    &.btn-primary {
      background-color: $primary-color;
      color: #fff;

      &:hover {
        background-color: $primary-dark;
      }
    }

    &.btn-outline {
      border-color: $medium-grey;
      color: $text-secondary;

      &:hover {
        background-color: $medium-grey;
        color: #fff;
      }
    }

    &.btn-sm {
      min-height: 30px;
      padding: 0.3rem 0.65rem;
      font-size: 0.78rem;
    }

    &.btn-save {
      background-color: $primary-color;
      color: #fff;
    }
  }

  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.65);
    z-index: 1000;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 1rem;
  }

  .modal {
    background-color: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    padding: 1.5rem;
    width: 520px;
    max-width: 100%;
    max-height: calc(100vh - 2rem);
    overflow: auto;

    &.modal-wide {
      width: 980px;
    }
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
    margin-bottom: 1rem;

    h3 {
      color: $primary-light;
      margin: 0 0 0.25rem;
    }

    p {
      margin: 0;
      color: $text-secondary;
    }
  }

  .tabs {
    display: flex;
    gap: 0.4rem;
    border-bottom: 1px solid $medium-grey;
    margin-bottom: 1rem;
    overflow-x: auto;

    button {
      min-height: 40px;
      padding: 0 0.85rem;
      background: transparent;
      border: none;
      color: $text-secondary;
      cursor: pointer;
      white-space: nowrap;
      border-bottom: 2px solid transparent;

      &.active {
        color: $primary-light;
        border-color: $primary-light;
      }
    }
  }

  .detail-panel {
    min-height: 260px;
  }

  .detail-loading {
    padding: 2rem;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.9rem;

    div {
      border: 1px solid rgba($medium-grey, 0.8);
      border-radius: $border-radius;
      padding: 0.9rem;
      background-color: rgba($background-color, 0.55);
    }

    span {
      display: block;
      color: $text-disabled;
      font-size: 0.78rem;
      margin-bottom: 0.35rem;
    }

    strong {
      color: $text-primary;
      font-size: 0.96rem;
    }
  }

  .panel-title {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-end;
    margin-bottom: 0.8rem;

    h4 {
      color: $text-primary;
      margin: 0;
    }

    span {
      color: $text-disabled;
      font-size: 0.82rem;
    }
  }

  .mini-table {
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    overflow: hidden;
    display: table;

    th,
    td {
      font-size: 0.86rem;
    }
  }

  .inline-input,
  .guest-motor-form input,
  textarea {
    width: 100%;
    padding: 0.48rem 0.65rem;
    background-color: $background-color;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    color: $text-primary;
    font-size: 0.86rem;
    box-sizing: border-box;

    &:focus {
      outline: none;
      border-color: $primary-color;
    }
  }

  .action-cell {
    display: flex;
    gap: 0.4rem;
  }

  .guest-motor-form {
    margin-top: 1.2rem;
    padding-top: 1rem;
    border-top: 1px solid $medium-grey;

    h4 {
      color: $text-primary;
      margin: 0 0 0.8rem;
    }
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.8rem;
    margin-bottom: 1rem;

    label {
      color: $text-secondary;
      font-size: 0.82rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }
  }

  .text-muted,
  .empty-text {
    color: $text-disabled;
    font-size: 0.9rem;
  }

  textarea {
    min-height: 160px;
    resize: vertical;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 1rem;
  }

  @media (max-width: 768px) {
    .section-header {
      align-items: stretch;
    }

    .toolbar {
      width: 100%;

      input,
      select,
      .btn {
        width: 100%;
      }
    }

    .info-grid,
    .form-grid {
      grid-template-columns: 1fr;
    }

    .modal {
      padding: 1rem;
    }

    .modal-header,
    .panel-title {
      flex-direction: column;
      align-items: stretch;
    }
  }
}
</style>
