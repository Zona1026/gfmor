<template>
  <div class="admin-bookings">
    <div class="header-actions">
      <h2>預約管理</h2>
      <div class="actions">
        <input type="date" v-model="filterDate" @change="fetchBookings" class="date-picker" />
        <select v-model="filterStatus" @change="fetchBookings" class="status-filter">
          <option value="">全部狀態</option>
          <option v-for="(label, key) in bookingStatusMap" :key="key" :value="key">{{ label }}</option>
        </select>
        <button class="btn btn-outline" @click="handleFilterToday">今日預約</button>
        <button class="btn btn-danger" @click="showCloseModal = true">封鎖時段</button>
        <button class="btn btn-primary" @click="showAddModal = true">新增預約</button>
      </div>
    </div>

    <div class="table-container">
      <table v-if="!loading && bookings.length > 0">
        <thead>
          <tr>
            <th>預約日期 / 時間</th>
            <th>客戶資料</th>
            <th>車輛資料</th>
            <th>預約項目</th>
            <th>備註</th>
            <th>狀態</th>
            <th>工單狀態</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="booking in bookings"
            :key="booking.id"
            :class="{ 'row-closed': booking.status === 'SYSTEM_CLOSED' }"
          >
            <td>
              <strong>{{ formatDate(booking.booking_time) }}</strong>
              <span class="secondary-line">{{ formatTime(booking.booking_time) }}</span>
            </td>

            <td v-if="booking.status === 'SYSTEM_CLOSED'" colspan="2" class="text-center text-muted">
              此時段已封鎖
            </td>
            <template v-else>
              <td>
                <strong>{{ booking.user?.name || '-' }}</strong>
                <span class="secondary-line">{{ booking.user?.phone || '-' }}</span>
              </td>
              <td>
                <strong>{{ booking.motor?.license_plate || '-' }}</strong>
                <span class="secondary-line">{{ booking.motor?.model_name || '-' }}</span>
              </td>
            </template>

            <td>{{ bookingCategoryMap[booking.category] || booking.category }}</td>
            <td class="note-cell">{{ booking.notes || '-' }}</td>
            <td>
              <select
                v-if="canEditStatus(booking)"
                v-model="booking.status"
                @change="handleStatusChange(booking, $event.target.value)"
                :class="statusClass(booking.status)"
              >
                <option v-for="option in editableStatusOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
              <span v-else class="status-badge" :class="statusClass(booking.status)">
                {{ bookingStatusMap[booking.status] || booking.status }}
              </span>
            </td>
            <td>
              <div class="work-order-actions">
                <button
                  v-if="booking.work_order"
                  class="btn btn-link"
                  @click="goToWorkOrder(booking.work_order.id)"
                >
                  查看工單 #{{ booking.work_order.id }}
                </button>
                <button
                  v-else
                  class="btn btn-convert"
                  :disabled="!canConvertToWorkOrder(booking) || convertingId === booking.id"
                  @click="handleConvertToWorkOrder(booking)"
                >
                  {{ convertingId === booking.id ? '建立中...' : '轉成工單' }}
                </button>
                <span v-if="booking.work_order" class="secondary-line">
                  {{ workOrderStatusMap[booking.work_order.status] || booking.work_order.status }}
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="loading" class="empty-state">載入中...</div>
      <div v-else class="empty-state">目前沒有符合條件的預約。</div>
    </div>

    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-content">
        <h3>新增預約</h3>
        <div class="form-group row">
          <input type="text" v-model="searchQuery" placeholder="輸入客戶姓名搜尋..." @keyup.enter="handleSearchUser" />
          <button class="btn btn-outline" @click="handleSearchUser">搜尋</button>
        </div>

        <div v-if="searchResults.length > 0" class="search-results">
          <label>選擇客戶與車輛</label>
          <select v-model="selectedMotorData" class="motor-select">
            <option disabled value="">請選擇...</option>
            <optgroup v-for="user in searchResults" :key="user.google_id" :label="user.name">
              <option v-for="motor in user.motors" :key="motor.id" :value="{ user, motor }">
                {{ motor.license_plate }} - {{ motor.model_name || '未填車型' }}
              </option>
            </optgroup>
          </select>
        </div>

        <form @submit.prevent="submitAddBooking" v-if="selectedMotorData">
          <div class="form-group row">
            <div class="field-stack">
              <label>預約日期</label>
              <DatePicker v-model="addForm.date" />
            </div>
            <div class="field-stack">
              <label>預約時間</label>
              <select v-model="addForm.time" required>
                <option value="" disabled>請選擇時間</option>
                <option v-for="t in availableSlotsForAdd" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>預約項目</label>
            <select v-model="addForm.category" required>
              <option value="MAINTENANCE">保養</option>
              <option value="REPAIR">維修</option>
              <option value="CONSULTATION">諮詢</option>
            </select>
          </div>
          <div class="form-group checkbox-group">
            <label>
              <input type="checkbox" v-model="addForm.force" />
              強制建立，同時段已有預約也建立
            </label>
          </div>
          <div class="form-group">
            <label>備註</label>
            <textarea v-model="addForm.notes" rows="2"></textarea>
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="showAddModal = false">取消</button>
            <button type="submit" class="btn btn-primary">建立預約</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showCloseModal" class="modal-overlay" @click.self="showCloseModal = false">
      <div class="modal-content">
        <h3>封鎖時段</h3>
        <p class="text-muted">封鎖後該時段會顯示為不可預約。</p>
        <form @submit.prevent="submitCloseSlot">
          <div class="form-group row">
            <div class="field-stack">
              <label>封鎖日期</label>
              <DatePicker v-model="closeForm.date" />
            </div>
            <div class="field-stack">
              <label>封鎖時間</label>
              <select v-model="closeForm.time" required>
                <option value="" disabled>請選擇時間</option>
                <option v-for="t in availableSlotsForClose" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="showCloseModal = false">取消</button>
            <button type="submit" class="btn btn-danger">確認封鎖</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  createWorkOrder,
  getAdminBookings,
  forceCreateBooking,
  updateBookingStatus,
  searchUsersByName,
  closeTimeslot
} from '../../api/admin';
import DatePicker from '../../components/common/DatePicker.vue';

const route = useRoute();
const router = useRouter();
const bookings = ref([]);
const loading = ref(false);
const convertingId = ref(null);
const filterDate = ref(typeof route.query.date === 'string' ? route.query.date : '');
const filterStatus = ref(typeof route.query.status === 'string' ? route.query.status : '');

const showAddModal = ref(false);
const showCloseModal = ref(false);

const searchQuery = ref('');
const searchResults = ref([]);
const selectedMotorData = ref('');
const addForm = ref({
  date: '',
  time: '',
  category: 'MAINTENANCE',
  notes: '',
  force: false
});

const closeForm = ref({
  date: '',
  time: ''
});

const bookingCategoryMap = {
  REPAIR: '維修',
  MAINTENANCE: '保養',
  CONSULTATION: '諮詢'
};

const bookingStatusMap = {
  PENDING: '預約中',
  CONFIRMED: '已確認',
  ARRIVED: '已到店',
  CONVERTED_TO_WORK_ORDER: '已轉工單',
  CANCELED: '已取消',
  NO_SHOW: '未到',
  TIMEOUT: '已逾時',
  COMPLETED: '已結案',
  SYSTEM_CLOSED: '時段封鎖'
};

const workOrderStatusMap = {
  PENDING: '待檢查',
  INSPECTION_PENDING: '待檢查',
  QUOTE_PENDING: '待報價',
  CUSTOMER_CONFIRMATION_PENDING: '等待客戶確認',
  SUPERVISOR_APPROVAL_PENDING: '待主管確認',
  IN_PROGRESS: '進行中',
  AWAITING_PAYMENT: '待收款',
  COMPLETED: '已完工',
  CANCELED: '已取消'
};

const editableStatusOptions = [
  { value: 'PENDING', label: '預約中' },
  { value: 'CONFIRMED', label: '已確認' },
  { value: 'ARRIVED', label: '已到店' },
  { value: 'CANCELED', label: '已取消' },
  { value: 'NO_SHOW', label: '未到' },
  { value: 'TIMEOUT', label: '已逾時' },
  { value: 'COMPLETED', label: '已結案' }
];

const convertableStatuses = ['PENDING', 'CONFIRMED', 'ARRIVED'];

const getBusinessSlots = (dateStr) => {
  if (!dateStr) return [];
  const selectedDate = new Date(dateStr);
  const dayOfWeek = selectedDate.getDay();
  if (dayOfWeek === 0) return [];

  let startHour = 13;
  let endHour = 21;
  if (dayOfWeek === 6) startHour = 11;

  const slots = [];
  for (let h = startHour; h <= endHour; h++) {
    const hh = h.toString().padStart(2, '0');
    slots.push(`${hh}:00`);
    slots.push(`${hh}:30`);
  }
  return slots;
};

const availableSlotsForAdd = computed(() => getBusinessSlots(addForm.value.date));
const availableSlotsForClose = computed(() => getBusinessSlots(closeForm.value.date));

const formatDate = (isoString) => {
  if (!isoString) return '-';
  const d = new Date(isoString);
  return d.toLocaleDateString('zh-TW');
};

const formatTime = (isoString) => {
  if (!isoString) return '-';
  const d = new Date(isoString);
  return d.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' });
};

const statusClass = (status) => `status-${String(status || '').toLowerCase().replaceAll('_', '-')}`;

const canEditStatus = (booking) => {
  return !['SYSTEM_CLOSED', 'CONVERTED_TO_WORK_ORDER'].includes(booking.status);
};

const canConvertToWorkOrder = (booking) => {
  return !booking.work_order && convertableStatuses.includes(booking.status);
};

const fetchBookings = async () => {
  loading.value = true;
  try {
    const params = { skip: 0, limit: 100 };
    if (filterDate.value) params.date_str = filterDate.value;
    const data = await getAdminBookings(params);
    bookings.value = filterStatus.value
      ? data.filter(booking => booking.status === filterStatus.value)
      : data;
  } catch (error) {
    console.error('載入預約失敗:', error);
  } finally {
    loading.value = false;
  }
};

const handleFilterToday = () => {
  const today = new Date();
  filterDate.value = today.toLocaleDateString('en-CA');
  filterStatus.value = '';
  fetchBookings();
};

const handleStatusChange = async (booking, newStatus) => {
  try {
    await updateBookingStatus(booking.id, { status: newStatus });
    await fetchBookings();
  } catch (error) {
    alert(`狀態更新失敗：${getErrorMessage(error)}`);
    await fetchBookings();
  }
};

const handleConvertToWorkOrder = async (booking) => {
  if (!canConvertToWorkOrder(booking)) return;
  const ok = window.confirm(`確定要將預約 #${booking.id} 轉成工單？`);
  if (!ok) return;

  convertingId.value = booking.id;
  try {
    const workOrder = await createWorkOrder({
      booking_id: booking.id,
      notes: booking.notes || '',
      items: []
    });
    await fetchBookings();
    alert(`已建立工單 #${workOrder.id}`);
  } catch (error) {
    alert(`建立工單失敗：${getErrorMessage(error)}`);
    await fetchBookings();
  } finally {
    convertingId.value = null;
  }
};

const goToWorkOrder = (workOrderId) => {
  router.push({ path: '/admin/work-orders', query: { q: String(workOrderId) } });
};

const getErrorMessage = (error) => {
  const detail = error.response?.data?.detail;
  if (!detail) return '未知錯誤';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(d => `${d.msg} (${d.loc.join('.')})`).join('\n');
  }
  return JSON.stringify(detail);
};

const handleSearchUser = async () => {
  if (!searchQuery.value) return;
  try {
    const data = await searchUsersByName(searchQuery.value);
    searchResults.value = data.filter(u => u.motors && u.motors.length > 0);
    if (searchResults.value.length === 0) {
      alert('找不到有車輛資料的客戶。');
    }
  } catch (error) {
    console.error(error);
  }
};

const submitAddBooking = async () => {
  if (!selectedMotorData.value || !addForm.value.date || !addForm.value.time) return;

  const bookingTimeStr = `${addForm.value.date}T${addForm.value.time}:00`;
  const payload = {
    google_id: selectedMotorData.value.user.google_id,
    motor_id: selectedMotorData.value.motor.id,
    booking_time: bookingTimeStr,
    category: addForm.value.category,
    notes: addForm.value.notes,
    force: addForm.value.force
  };

  try {
    await forceCreateBooking(payload);
    showAddModal.value = false;
    selectedMotorData.value = '';
    searchQuery.value = '';
    searchResults.value = [];
    addForm.value.notes = '';
    await fetchBookings();
  } catch (error) {
    alert(`新增失敗：${getErrorMessage(error)}`);
  }
};

const submitCloseSlot = async () => {
  if (!closeForm.value.date || !closeForm.value.time) return;

  try {
    const bookingTimeStr = `${closeForm.value.date}T${closeForm.value.time}:00`;
    await closeTimeslot(bookingTimeStr);
    showCloseModal.value = false;
    await fetchBookings();
  } catch (error) {
    alert(`封鎖失敗：${getErrorMessage(error)}`);
  }
};

onMounted(() => {
  fetchBookings();
});
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-bookings {
  color: $text-primary;

  .header-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;

    h2 {
      margin: 0;
      color: $primary-light;
    }

    .actions {
      display: flex;
      gap: 0.8rem;
      align-items: center;
      flex-wrap: wrap;

      .date-picker,
      .status-filter {
        padding: 0.5rem;
        background-color: $dark-grey;
        color: $text-primary;
        border: 1px solid $medium-grey;
        border-radius: $border-radius;
      }
    }
  }

  .btn {
    padding: 0.55rem 0.9rem;
    border: none;
    border-radius: $border-radius;
    cursor: pointer;
    font-size: 0.88rem;
    font-weight: 700;
    transition: 0.2s;
    white-space: nowrap;

    &:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }

    &-primary {
      background-color: $primary-color;
      color: #fff;
      &:hover { background-color: $primary-dark; }
    }

    &-danger {
      background-color: transparent;
      border: 1px solid #ff5252;
      color: #ff5252;
      &:hover { background-color: rgba(#ff5252, 0.1); }
    }

    &-outline {
      background-color: transparent;
      border: 1px solid $medium-grey;
      color: $text-secondary;
      &:hover { border-color: $primary-light; color: $primary-light; }
    }

    &-convert {
      background-color: rgba($primary-color, 0.16);
      border: 1px solid rgba($primary-color, 0.55);
      color: $primary-light;
    }

    &-link {
      padding: 0;
      background: transparent;
      color: $primary-light;
      text-align: left;

      &:hover {
        text-decoration: underline;
      }
    }
  }

  .table-container {
    background-color: $background-color;
    border-radius: $border-radius;
    padding: 1rem;
    border: 1px solid $medium-grey;
    overflow-x: auto;

    table {
      width: 100%;
      border-collapse: collapse;

      th,
      td {
        padding: 0.9rem;
        text-align: left;
        border-bottom: 1px solid $medium-grey;
        vertical-align: top;
      }

      th {
        color: $primary-light;
        font-weight: 600;
        white-space: nowrap;
      }

      .row-closed {
        background-color: rgba(#000, 0.2);

        td {
          color: $text-disabled;
        }
      }

      select {
        min-width: 112px;
        padding: 0.4rem;
        background-color: $dark-grey;
        color: $text-primary;
        border: 1px solid $medium-grey;
        border-radius: $border-radius;
        outline: none;
      }
    }

    .empty-state {
      padding: 3rem;
      text-align: center;
      color: $text-disabled;
    }
  }

  .secondary-line {
    display: block;
    margin-top: 0.25rem;
    color: $text-secondary;
    font-size: 0.82rem;
  }

  .note-cell {
    min-width: 160px;
    max-width: 240px;
    white-space: normal;
  }

  .work-order-actions {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.35rem 0.65rem;
    border-radius: 999px;
    font-size: 0.82rem;
    background-color: rgba($medium-grey, 0.4);
  }

  .status-pending { color: #64b5f6; }
  .status-confirmed { color: #4fc3f7; }
  .status-arrived { color: #81c784; }
  .status-converted-to-work-order { color: #b39ddb; background-color: rgba(#b39ddb, 0.15); }
  .status-completed { color: #81c784; }
  .status-timeout { color: #ffb74d; }
  .status-canceled,
  .status-no-show { color: #e57373; }
  .status-system-closed { color: #9e9e9e; background-color: #424242; }

  .text-center { text-align: center; }
  .text-muted { color: $text-disabled; }

  .modal-overlay {
    position: fixed;
    inset: 0;
    background-color: rgba(0, 0, 0, 0.7);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;

    .modal-content {
      background-color: $dark-grey;
      padding: 2.5rem;
      border-radius: $border-radius;
      width: min(92vw, 520px);
      border: 1px solid $medium-grey;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);

      h3 {
        margin-top: 0;
        margin-bottom: 1.5rem;
        color: $primary-light;
      }

      .row {
        display: flex;
        gap: 0.75rem;

        input {
          flex: 1;
        }
      }

      .field-stack {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
      }

      .search-results {
        margin-bottom: 1.5rem;
        padding: 1rem;
        background-color: $background-color;
        border-radius: $border-radius;

        .motor-select {
          width: 100%;
          margin-top: 0.5rem;
        }
      }

      .form-group {
        margin-bottom: 1.2rem;
        display: flex;
        flex-direction: column;

        label {
          font-size: 0.9rem;
          color: $text-secondary;
          margin-bottom: 0.4rem;
        }

        &.checkbox-group {
          flex-direction: row;
          align-items: center;

          label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin: 0;
            color: #ffb74d;
          }
        }

        input,
        select,
        textarea {
          padding: 0.8rem;
          border-radius: $border-radius;
          border: 1px solid $medium-grey;
          background-color: $background-color;
          color: $text-primary;
          font-family: inherit;

          &:focus {
            outline: none;
            border-color: $primary-light;
          }
        }
      }

      .form-actions {
        display: flex;
        justify-content: flex-end;
        gap: 1rem;
        margin-top: 2rem;
      }
    }
  }

  @media (max-width: 768px) {
    .header-actions {
      flex-direction: column;
      align-items: stretch;

      .actions {
        flex-direction: column;
        align-items: stretch;

        .btn,
        .date-picker,
        .status-filter {
          width: 100%;
        }
      }
    }

    .modal-overlay .modal-content .row {
      flex-direction: column;
    }
  }
}
</style>
