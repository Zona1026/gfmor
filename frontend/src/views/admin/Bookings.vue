<template>
  <div class="admin-bookings">
    <div class="header-actions">
      <h2>預約管理系統</h2>
      <div class="actions">
        <input type="date" v-model="filterDate" @change="fetchBookings" class="date-picker" />
        <button class="btn btn-outline" @click="handleFilterToday">今日預約</button>
        <button class="btn btn-danger" @click="showCloseModal = true">關閉時段</button>
        <button class="btn btn-primary" @click="showAddModal = true">手動新增預約</button>
      </div>
    </div>

    <div class="table-container">
      <table v-if="!loading && bookings.length > 0">
        <thead>
          <tr>
            <th>預約時間</th>
            <th>車主</th>
            <th>電話</th>
            <th>車牌 (車種)</th>
            <th>服務項目</th>
            <th>備註</th>
            <th>狀態</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="booking in bookings" :key="booking.id" :class="{'row-closed': booking.status === '時段關閉'}">
            <td>{{ formatDateTime(booking.booking_time) }}</td>
            <td v-if="booking.status === '時段關閉'" colspan="3" class="text-center text-muted">-- 系統保留不開放 --</td>
            <template v-else>
              <td>{{ booking.user.name }}</td>
              <td>{{ booking.user.phone || '無' }}</td>
              <td>{{ booking.motor.license_plate }} ({{ booking.motor.model_name || '無' }})</td>
            </template>
            <td>{{ booking.category }}</td>
            <td>{{ booking.notes || '-' }}</td>
            <td>
              <select v-if="booking.status !== 'SYSTEM_CLOSED'" 
                      v-model="booking.status" 
                      @change="handleStatusChange(booking, $event.target.value)"
                      :class="statusClass(booking.status)">
                <option v-for="(label, key) in bookingStatusMap" :key="key" :value="key">{{ label }}</option>
              </select>
              <span v-else class="status-badge closed">時段關閉</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="loading" class="empty-state">載入中...</div>
      <div v-else class="empty-state">目前沒有任何預約紀錄。</div>
    </div>

    <!-- 手動新增預約 Modal -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-content">
        <h3>手動新增客戶預約</h3>
        <div class="form-group row">
          <input type="text" v-model="searchQuery" placeholder="輸入客戶姓名搜尋..." @keyup.enter="handleSearchUser" />
          <button class="btn btn-outline" @click="handleSearchUser">搜尋</button>
        </div>
        
        <div v-if="searchResults.length > 0" class="search-results">
          <label>請選擇客戶與車輛：</label>
          <select v-model="selectedMotorData" class="motor-select">
            <option disabled value="">請選擇...</option>
            <optgroup v-for="user in searchResults" :key="user.google_id" :label="user.name">
              <option v-for="motor in user.motors" :key="motor.id" :value="{ user, motor }">
                {{ motor.license_plate }} - {{ motor.model_name || '未知' }}
              </option>
            </optgroup>
          </select>
        </div>

        <form @submit.prevent="submitAddBooking" v-if="selectedMotorData">
          <div class="form-group row">
            <div style="flex:1; display:flex; flex-direction:column; gap:0.4rem;">
              <label>預約日期：</label>
              <DatePicker v-model="addForm.date" />
            </div>
            <div style="flex:1; display:flex; flex-direction:column; gap:0.4rem;">
              <label>預約時段：</label>
              <select v-model="addForm.time" required>
                <option value="" disabled>請選擇時間</option>
                <option v-for="t in availableSlotsForAdd" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>服務類別：</label>
            <select v-model="addForm.category" required>
              <option value="MAINTENANCE">保養</option>
              <option value="REPAIR">維修</option>
              <option value="CONSULTATION">諮詢</option>
            </select>
          </div>
          <div class="form-group checkbox-group">
            <label>
              <input type="checkbox" v-model="addForm.force" />
              強制建立 (略過時段容量限制)
            </label>
          </div>
          <div class="form-group">
            <label>備註：</label>
            <textarea v-model="addForm.notes" rows="2"></textarea>
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="showAddModal = false">取消</button>
            <button type="submit" class="btn btn-primary">確定預約</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 關閉時段 Modal -->
    <div v-if="showCloseModal" class="modal-overlay" @click.self="showCloseModal = false">
      <div class="modal-content">
        <h3>關閉特定時段</h3>
        <p class="text-muted">關閉後，客戶將無法在此時段進行預約。</p>
        <form @submit.prevent="submitCloseSlot">
          <div class="form-group row">
            <div style="flex:1; display:flex; flex-direction:column; gap:0.4rem;">
              <label>關閉日期：</label>
              <DatePicker v-model="closeForm.date" />
            </div>
            <div style="flex:1; display:flex; flex-direction:column; gap:0.4rem;">
              <label>關閉時段：</label>
              <select v-model="closeForm.time" required>
                <option value="" disabled>請選擇時間</option>
                <option v-for="t in availableSlotsForClose" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="showCloseModal = false">取消</button>
            <button type="submit" class="btn btn-danger">確定關閉</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { getAdminBookings, forceCreateBooking, updateBookingStatus, searchUsersByName, closeTimeslot } from '../../api/admin';
import DatePicker from '../../components/common/DatePicker.vue';

const bookings = ref([]);
const loading = ref(false);
const filterDate = ref('');

const showAddModal = ref(false);
const showCloseModal = ref(false);

// Add Booking State
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

// Close Slot State
const closeForm = ref({
  date: '',
  time: ''
});

// strictly enforce business hours
const getBusinessSlots = (dateStr) => {
  if (!dateStr) return [];
  const selectedDate = new Date(dateStr);
  const dayOfWeek = selectedDate.getDay();
  if (dayOfWeek === 0) return []; // Sunday closed
  
  let startHour = 13;
  let endHour = 21; // 結束營業為 22:00，最後預約時間為 21:30
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

const formatDateTime = (isoString) => {
  if (!isoString) return '';
  const d = new Date(isoString);
  return `${d.toLocaleDateString('zh-TW')} ${d.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })}`;
};

const bookingStatusMap = {
  'PENDING': '預約中',
  'COMPLETED': '已結案',
  'TIMEOUT': '已超時',
  'CANCELED': '預約取消'
};

const statusClass = (status) => {
  return {
    'status-pending': status === 'PENDING',
    'status-completed': status === 'COMPLETED',
    'status-timeout': status === 'TIMEOUT',
    'status-canceled': status === 'CANCELED'
  };
};

const fetchBookings = async () => {
  loading.value = true;
  try {
    const params = { skip: 0, limit: 100 };
    if (filterDate.value) {
      params.date_str = filterDate.value;
    }
    const data = await getAdminBookings(params);
    bookings.value = data;
  } catch (error) {
    console.error('API Error:', error);
  } finally {
    loading.value = false;
  }
};

const handleFilterToday = () => {
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const dd = String(today.getDate()).padStart(2, '0');
  filterDate.value = `${yyyy}-${mm}-${dd}`;
  fetchBookings();
};

const handleStatusChange = async (booking, newStatus) => {
  try {
    await updateBookingStatus(booking.id, { status: newStatus });
    alert('狀態更新成功！');
  } catch (error) {
    alert('狀態更新失敗：' + getErrorMessage(error));
    fetchBookings(); // 失敗時重新拉取資料重置畫面
  }
};

const getErrorMessage = (error) => {
  const detail = error.response?.data?.detail;
  if (!detail) return '未知的錯誤';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    // 處理 FastAPI 的 422 驗證錯誤
    return detail.map(d => `${d.msg} (欄位: ${d.loc.join('.')})`).join('\n');
  }
  return JSON.stringify(detail);
};

const handleSearchUser = async () => {
  if (!searchQuery.value) return;
  try {
    const data = await searchUsersByName(searchQuery.value);
    searchResults.value = data.filter(u => u.motors && u.motors.length > 0);
    if(searchResults.value.length === 0) {
      alert("找不到符合的客戶，或該客戶沒有愛車資料。");
    }
  } catch(error) {
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
    alert('手動新增成功！');
    showAddModal.value = false;
    fetchBookings();
    
    // Reset
    selectedMotorData.value = '';
    searchQuery.value = '';
    searchResults.value = [];
  } catch (error) {
    alert('新增失敗：' + getErrorMessage(error));
  }
};

const submitCloseSlot = async () => {
  if (!closeForm.value.date || !closeForm.value.time) return;
  
  try {
    const bookingTimeStr = `${closeForm.value.date}T${closeForm.value.time}:00`;
    await closeTimeslot(bookingTimeStr);
    alert('時段已關閉！');
    showCloseModal.value = false;
    fetchBookings();
  } catch (error) {
    alert('關閉失敗：' + getErrorMessage(error));
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
    margin-bottom: 1.5rem;

    h2 {
      margin: 0;
      color: $primary-light;
    }

    .actions {
      display: flex;
      gap: 0.8rem;
      align-items: center;

      .date-picker {
        padding: 0.5rem;
        background-color: $dark-grey;
        color: $text-primary;
        border: 1px solid $medium-grey;
        border-radius: $border-radius;
      }
    }

    @media (max-width: 768px) {
      flex-direction: column;
      align-items: stretch;
      gap: 1.2rem;
      margin-bottom: 2rem;

      h2 {
        background-color: rgba($primary-color, 0.1);
        padding: 0.8rem;
        border-radius: $border-radius;
        text-align: center;
        border-left: 4px solid $primary-color;
      }

      .actions {
        flex-direction: column;
        align-items: stretch;
        
        .date-picker {
          width: 100%;
        }

        .btn {
          width: 100%;
        }
      }
    }
  }

  .btn {
    padding: 0.6rem 1rem;
    border: none;
    border-radius: $border-radius;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: bold;
    transition: 0.3s;

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
      
      th, td {
        padding: 1rem;
        text-align: left;
        border-bottom: 1px solid $medium-grey;
      }

      th {
        color: $primary-light;
        font-weight: 600;
      }

      .row-closed {
        background-color: rgba(#000, 0.2);
        td { color: $text-disabled; }
      }

      select {
        padding: 0.4rem;
        background-color: $dark-grey;
        color: $text-primary;
        border: 1px solid $medium-grey;
        border-radius: $border-radius;
        outline: none;

        &.status-pending { color: #64b5f6; }
        &.status-completed { color: #81c784; }
        &.status-timeout { color: #ffb74d; }
        &.status-canceled { color: #e57373; }
      }

      .status-badge {
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        &.closed {
          background-color: #424242;
          color: #9e9e9e;
        }
      }
    }
    
    .empty-state {
      padding: 3rem;
      text-align: center;
      color: $text-disabled;
    }
  }

  .text-center { text-align: center; }
  .text-muted { color: $text-disabled; }

  // Modal styles
  .modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-color: rgba(0,0,0,0.7);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;

    .modal-content {
      background-color: $dark-grey;
      padding: 2.5rem;
      border-radius: $border-radius;
      width: 100%;
      max-width: 500px;
      border: 1px solid $medium-grey;
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);

      h3 {
        margin-top: 0;
        margin-bottom: 1.5rem;
        color: $primary-light;
      }

      .row {
        display: flex;
        gap: 0.5rem;
        input { flex: 1; }
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
            color: #ffb74d; // Highlight warning mode
          }
        }

        input, select, textarea {
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
}
</style>
