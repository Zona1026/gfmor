<template>
  <div class="member-center-page">
    <h2>會員中心</h2>
    <p class="subtitle">歡迎回來，{{ user?.name }}！以下是您的個人與車輛資訊。</p>
    
    <div v-if="user" class="profile-container">
      <!-- 頭像與基本資料 -->
      <div class="card user-info-card">
        <div class="info-details">
          <div class="header-row">
            <h3>基本資料</h3>
            <button @click="startEdit" v-if="!isEditing" class="btn-edit">編輯資料</button>
          </div>

          <form v-if="isEditing" @submit.prevent="saveProfile" class="edit-form">
            <div class="form-group">
              <label>姓名：</label>
              <input v-model="editForm.name" required />
            </div>
            <div class="form-group">
              <label>手機號碼：</label>
              <input v-model="editForm.phone" />
            </div>
            <div class="actions">
              <button type="submit" class="btn-save">儲存</button>
              <button type="button" @click="isEditing = false" class="btn-cancel">取消</button>
            </div>
          </form>

          <div v-else>
            <div class="info-group">
              <span class="label">姓名：</span>
              <span class="value">{{ user.name }}</span>
            </div>
            <div class="info-group">
              <span class="label">Email：</span>
              <span class="value">{{ user.email }}</span>
            </div>
            <div class="info-group">
              <span class="label">手機號碼：</span>
              <span class="value">{{ user.phone || '尚未提供' }}</span>
            </div>
            <div class="info-group">
              <span class="label">會員等級：</span>
              <span class="value">{{ user.membership_level || '一般會員' }}</span>
            </div>
            <div class="info-group">
              <span class="label">累積消費：</span>
              <span class="value">${{ user.cumulative_consumption || 0 }}</span>
            </div>
            <div class="info-group">
              <span class="label">目前點數：</span>
              <span class="value">{{ pointSummary.current_points }}</span>
            </div>
            <div class="info-group">
              <span class="label">快到期點數：</span>
              <span class="value">{{ pointSummary.expiring_soon_points }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 我的愛車 -->
      <div class="card motors-card">
        <div class="header-row">
          <h3>我的愛車</h3>
          <button @click="startAddMotor" v-if="!isAddingMotor" class="btn-primary-outline">新增愛車</button>
        </div>

        <!-- 新增愛車表單 -->
        <form v-if="isAddingMotor" @submit.prevent="saveNewMotor" class="motor-form new-motor-form">
          <h4 style="margin-bottom: 1rem; color: #fff;">新增車輛</h4>
          <div class="motor-edit-fields">
            <input v-model="newMotorForm.brand" placeholder="廠牌 (如 YAMAHA)" required />
            <input v-model="newMotorForm.model_name" placeholder="型號 (如 勁戰六代)" required />
            <input v-model="newMotorForm.license_plate" placeholder="車牌 (如 ABC-1234)" required />
            <label class="new-vehicle-toggle">
              <input v-model="newMotorForm.is_new_vehicle" type="checkbox" />
              <span>新車</span>
            </label>
            <input v-if="newMotorForm.is_new_vehicle" v-model="newMotorForm.purchase_date" type="date" aria-label="購車日期" />
          </div>
          <div class="actions">
            <button type="submit" class="btn-save">儲存新增</button>
            <button type="button" @click="isAddingMotor = false" class="btn-cancel">取消</button>
          </div>
        </form>

        <div v-if="completeMotors && completeMotors.length > 0" class="motor-table-wrap">
          <table class="motor-table">
            <thead>
              <tr>
                <th>車牌</th>
                <th>廠牌</th>
                <th>型號</th>
                <th>保養紀錄</th>
                <th class="motor-action-heading">操作</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="motor in completeMotors" :key="motor.id || motor.ID || motor.license_plate">
                <tr v-if="editingMotorId !== (motor.id || motor.ID)">
                  <td data-label="車牌"><strong>{{ motor.license_plate }}</strong></td>
                  <td data-label="廠牌">{{ motor.brand || '未填' }}</td>
                  <td data-label="型號">{{ motor.model_name || '未填' }}</td>
                  <td data-label="保養紀錄">
                    <span v-if="motor.is_new_vehicle" class="maintenance-status">
                      <button type="button" class="btn-record-detail vehicle-maintenance-button" @click="openVehicleMaintenance(motor)">查看紀錄</button>
                      <small v-if="motor.purchase_date">購車 {{ formatConsumptionDate(motor.purchase_date) }}</small>
                    </span>
                    <span v-else>不適用</span>
                  </td>
                  <td class="motor-actions">
                    <button @click="startEditMotor(motor)" class="btn-text">編輯</button>
                    <button @click="deleteMotorHandler(motor.id || motor.ID)" class="btn-text-danger">刪除</button>
                  </td>
                </tr>

                <tr v-else class="motor-edit-row">
                  <td colspan="5">
                    <form @submit.prevent="saveEditMotor(motor.id || motor.ID)" class="motor-form">
                      <div class="motor-edit-fields">
                        <input v-model="editMotorForm.brand" placeholder="廠牌" required />
                        <input v-model="editMotorForm.model_name" placeholder="型號" required />
                        <input v-model="editMotorForm.license_plate" placeholder="車牌" required />
                        <label class="new-vehicle-toggle">
                          <input v-model="editMotorForm.is_new_vehicle" type="checkbox" />
                          <span>新車</span>
                        </label>
                        <input v-if="editMotorForm.is_new_vehicle" v-model="editMotorForm.purchase_date" type="date" aria-label="購車日期" />
                      </div>
                      <div class="actions">
                        <button type="submit" class="btn-save">儲存修改</button>
                        <button type="button" @click="editingMotorId = null" class="btn-cancel">取消</button>
                      </div>
                    </form>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <p v-else-if="!isAddingMotor" class="no-motors">目前尚未登錄任何完整車輛資訊。</p>
      </div>

      <!-- 歷史紀錄 -->
      <div class="history-section">
        <div class="tabs">
          <button :class="{ active: activeTab === 'bookings' }" @click="activeTab = 'bookings'">預約紀錄</button>
          <button :class="{ active: activeTab === 'maintenance' }" @click="activeTab = 'maintenance'">保養 / 維修 / 改裝紀錄</button>
          <button :class="{ active: activeTab === 'points' }" @click="activeTab = 'points'">點數紀錄</button>
        </div>

        <p v-if="historyError" class="history-error">{{ historyError }}</p>

        <div class="action-bar" style="text-align: right; padding: 1rem 2rem 0;" v-if="activeTab === 'bookings'">
          <button @click="router.push('/booking')" class="btn-new-booking">我要預約</button>
        </div>

        <div v-if="activeTab === 'bookings'" class="tab-content">
          <div v-if="sortedBookings.length > 0" class="history-list">
            <div v-for="booking in sortedBookings" :key="booking.id" class="history-item">
              <div class="item-header">
                <strong>{{ new Date(booking.booking_time).toLocaleString() }}</strong>
                <span class="status" :class="booking.status">{{ bookingStatusMap[booking.status] || booking.status }}</span>
              </div>
              <div class="item-body">
                <p>服務項目: {{ bookingCategoryMap[booking.category] || booking.category }}</p>
                <p>備註: {{ booking.notes || '無' }}</p>
                
                <button 
                  v-if="booking.status === 'PENDING' && new Date(booking.booking_time) > new Date()"
                  @click="cancelBookingHandler(booking.id)"
                  class="btn-cancel-booking"
                >
                  取消預約
                </button>
              </div>
            </div>
          </div>
          <p v-else class="empty-state">尚無預約紀錄</p>
        </div>

        <div v-if="activeTab === 'maintenance'" class="tab-content">
          <div v-if="sortedMaintenanceRecords.length > 0" class="record-table-wrap">
            <table class="record-table maintenance-record-table">
              <thead>
                <tr>
                  <th>工單</th>
                  <th>項目</th>
                  <th>商品明細</th>
                  <th>價格</th>
                  <th>工單總額</th>
                  <th><span class="sr-only">操作</span></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in sortedMaintenanceRecords" :key="record.id">
                  <td data-label="工單">
                    <strong>#{{ record.id }}</strong>
                    <small>完工 {{ formatConsumptionDate(record.completed_at || record.consumption_date || record.created_at) }}</small>
                  </td>
                  <td data-label="項目">{{ serviceTypeMap[record.service_type] || record.service_type }}</td>
                  <td data-label="商品明細">{{ workOrderItemNames(record) }}</td>
                  <td data-label="價格">{{ workOrderItemPrices(record) }}</td>
                  <td data-label="工單總額" class="amount-cell">NT$ {{ formatNumber(record.total_amount) }}</td>
                  <td class="action-cell">
                    <button type="button" class="btn-record-detail" @click="openMaintenanceDetail(record)">查看詳細訂單紀錄</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="empty-state">尚無保養、維修或改裝紀錄</p>
        </div>

        <div v-if="activeTab === 'points'" class="tab-content">
          <div v-if="pointTransactions.length > 0" class="record-table-wrap">
            <table class="record-table point-record-table">
              <thead>
                <tr>
                  <th>來源</th>
                  <th>消費日期</th>
                  <th>商品名稱</th>
                  <th>點數異動</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="transaction in pointTransactions" :key="transaction.id">
                  <td data-label="來源">
                    <strong>{{ transaction.source_label }}</strong>
                    <small>{{ pointTypeMap[transaction.type] || transaction.type }}</small>
                  </td>
                  <td data-label="消費日期">{{ formatConsumptionDate(transaction.issued_at) }}</td>
                  <td data-label="商品名稱">{{ pointItemNames(transaction) }}</td>
                  <td data-label="點數異動" class="points-cell" :class="{ positive: transaction.points > 0, negative: transaction.points < 0 }">
                    {{ formatPointChange(transaction.points) }} 點
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="empty-state">尚無點數累積或使用紀錄</p>
        </div>
      </div>

      <div v-if="selectedMaintenanceRecord" class="record-modal-overlay" @click.self="closeMaintenanceDetail">
        <section class="record-modal" role="dialog" aria-modal="true" aria-labelledby="record-modal-title">
          <header class="record-modal-header">
            <div>
              <h2 id="record-modal-title">工單 #{{ selectedMaintenanceRecord.id }}</h2>
              <p>{{ serviceTypeMap[selectedMaintenanceRecord.service_type] || selectedMaintenanceRecord.service_type }} / {{ vehicleText(selectedMaintenanceRecord) }}</p>
            </div>
            <button type="button" class="record-modal-close" aria-label="關閉" @click="closeMaintenanceDetail">×</button>
          </header>

          <dl class="record-summary">
            <div><dt>完工日</dt><dd>{{ formatConsumptionDate(selectedMaintenanceRecord.completed_at || selectedMaintenanceRecord.consumption_date || selectedMaintenanceRecord.created_at) }}</dd></div>
            <div><dt>工單狀態</dt><dd>{{ workOrderStatusMap[selectedMaintenanceRecord.status] || selectedMaintenanceRecord.status }}</dd></div>
            <div><dt>付款狀態</dt><dd>{{ paymentStatusMap[selectedMaintenanceRecord.payment_status] || selectedMaintenanceRecord.payment_status }}</dd></div>
            <div><dt>里程</dt><dd>{{ selectedMaintenanceRecord.vehicle_mileage ? `${formatNumber(selectedMaintenanceRecord.vehicle_mileage)} km` : '未記錄' }}</dd></div>
          </dl>

          <div v-if="selectedMaintenanceRecord.problem_description || selectedMaintenanceRecord.inspection_result" class="record-notes">
            <p v-if="selectedMaintenanceRecord.problem_description"><strong>問題描述</strong>{{ selectedMaintenanceRecord.problem_description }}</p>
            <p v-if="selectedMaintenanceRecord.inspection_result"><strong>檢查結果</strong>{{ selectedMaintenanceRecord.inspection_result }}</p>
          </div>

          <div class="record-table-wrap">
            <table class="record-table detail-record-table">
              <thead><tr><th>類型</th><th>項目</th><th>數量</th><th>單價</th><th>小計</th></tr></thead>
              <tbody>
                <tr v-for="item in selectedMaintenanceRecord.line_items || []" :key="item.id">
                  <td data-label="類型">{{ lineItemTypeMap[item.type] || item.type }}</td>
                  <td data-label="項目">{{ item.name }}</td>
                  <td data-label="數量">{{ item.quantity || 1 }}</td>
                  <td data-label="單價">NT$ {{ formatNumber(item.unit_price) }}</td>
                  <td data-label="小計">NT$ {{ formatNumber(lineItemAmount(item)) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="record-total">工單總額 <strong>NT$ {{ formatNumber(selectedMaintenanceRecord.total_amount) }}</strong></div>
        </section>
      </div>

      <div v-if="selectedVehicleMaintenance" class="record-modal-overlay" @click.self="closeVehicleMaintenance">
        <section class="record-modal vehicle-maintenance-modal" role="dialog" aria-modal="true" aria-labelledby="vehicle-maintenance-title">
          <header class="record-modal-header">
            <div>
              <h2 id="vehicle-maintenance-title">{{ selectedVehicleMaintenance.motor.license_plate }} 保養紀錄</h2>
              <p>
                {{ [selectedVehicleMaintenance.motor.brand, selectedVehicleMaintenance.motor.model_name].filter(Boolean).join(' ') || '未填車型' }}
                <template v-if="selectedVehicleMaintenance.motor.purchase_date"> / 購車 {{ formatConsumptionDate(selectedVehicleMaintenance.motor.purchase_date) }}</template>
              </p>
            </div>
            <button type="button" class="record-modal-close" aria-label="關閉" @click="closeVehicleMaintenance">×</button>
          </header>

          <p v-if="vehicleMaintenanceLoading" class="maintenance-loading">載入保養紀錄中...</p>
          <p v-else-if="vehicleMaintenanceError" class="history-error">{{ vehicleMaintenanceError }}</p>
          <div v-else class="record-table-wrap">
            <table class="record-table vehicle-maintenance-table">
              <thead>
                <tr>
                  <th>保養里程</th>
                  <th>保養日期</th>
                  <th>實際里程</th>
                  <th>保養項目</th>
                  <th>備註</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in selectedVehicleMaintenance.records" :key="record.id">
                  <td data-label="保養里程"><strong>{{ formatNumber(record.target_mileage) }} km</strong></td>
                  <td data-label="保養日期">{{ formatConsumptionDate(record.service_date) }}</td>
                  <td data-label="實際里程">{{ record.actual_mileage == null ? '-' : `${formatNumber(record.actual_mileage)} km` }}</td>
                  <td data-label="保養項目">{{ vehicleMaintenanceItems(record) }}</td>
                  <td data-label="備註">{{ record.notes || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
    <div v-else class="loading">
      載入中或尚未登入...
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useAuthStore } from '../store/auth';
import { getUser, getUserPoints, getUserPointTransactions, updateUserProfile } from '../api/users';
import { getUserBookings, updateBooking } from '../api/bookings';
import { getUserWorkOrders } from '../api/workOrders';
import { deleteMotor, getMotorMaintenanceRecords, updateMotor } from '../api/motors';

const router = useRouter();
const authStore = useAuthStore();
const { user } = storeToRefs(authStore);

const activeTab = ref('bookings');
const bookings = ref([]);
const maintenanceRecords = ref([]);
const pointTransactions = ref([]);
const selectedMaintenanceRecord = ref(null);
const selectedVehicleMaintenance = ref(null);
const vehicleMaintenanceLoading = ref(false);
const vehicleMaintenanceError = ref('');
const historyError = ref('');
const pointSummary = ref({
  current_points: 0,
  expiring_soon_points: 0
});
const VEHICLE_DATA_UPDATED_KEY = 'vehicleDataUpdatedAt';

const bookingStatusMap = {
  'PENDING': '預約中',
  'CANCELED': '預約取消',
  'TIMEOUT': '已超時',
  'COMPLETED': '已結案',
  'SYSTEM_CLOSED': '時段關閉'
};

const bookingCategoryMap = {
  'REPAIR': '維修',
  'MAINTENANCE': '保養',
  'CONSULTATION': '諮詢'
};

const serviceTypeMap = {
  'REPAIR': '維修',
  'MAINTENANCE': '保養',
  'MODIFICATION': '改裝'
};

const workOrderStatusMap = {
  'PENDING': '待檢查',
  'INSPECTION_PENDING': '待檢查',
  'QUOTE_PENDING': '待報價',
  'CUSTOMER_CONFIRMATION_PENDING': '等待客戶確認',
  'SUPERVISOR_APPROVAL_PENDING': '待主管確認',
  'IN_PROGRESS': '施工中',
  'AWAITING_PAYMENT': '待收款',
  'COMPLETED': '已完工',
  'CANCELED': '已取消'
};

const paymentStatusMap = {
  'UNPAID': '未付款',
  'PARTIALLY_PAID': '部分付款',
  'PAID': '已付款',
  'REFUNDED': '已退款'
};

const lineItemTypeMap = {
  'SERVICE': '施工項目',
  'PART': '零件 / 耗材',
  'LABOR': '工資 / 服務費',
  'DISCOUNT': '折扣'
};

const pointTypeMap = {
  'EARN': '累積點數',
  'REDEEM': '使用點數',
  'EXPIRE': '點數到期',
  'REFUND_ADJUST': '退款回沖'
};

const sortedBookings = computed(() => {
  const now = new Date();
  const upcoming = [];
  const pastOrDone = [];
  
  bookings.value.forEach(b => {
    const bTime = new Date(b.booking_time);
    if (b.status === 'PENDING' && bTime > now) {
      upcoming.push(b);
    } else {
      pastOrDone.push(b);
    }
  });
  
  // 即將到來的預約，越近的排在越上面 (ASC)
  upcoming.sort((a, b) => new Date(a.booking_time) - new Date(b.booking_time));
  // 已經過去的預約，越近的(最新的)排在越上面 (DESC)
  pastOrDone.sort((a, b) => new Date(b.booking_time) - new Date(a.booking_time));
  
  return [...upcoming, ...pastOrDone];
});

const sortedMaintenanceRecords = computed(() => {
  return [...maintenanceRecords.value].sort((a, b) => {
    return new Date(b.scheduled_at || b.created_at) - new Date(a.scheduled_at || a.created_at);
  });
});

// Basic profile editing
const isEditing = ref(false);
const editForm = ref({ name: '', phone: '' });

// Motor editing & creating
const isAddingMotor = ref(false);
const newMotorForm = ref({ brand: '', model_name: '', license_plate: '', is_new_vehicle: false, purchase_date: '' });
const editingMotorId = ref(null);
const editMotorForm = ref({ brand: '', model_name: '', license_plate: '', is_new_vehicle: false, purchase_date: '' });

const completeMotors = computed(() => {
  if (!user.value || !user.value.motors) return [];
  return user.value.motors.filter(motor => motor.status !== '已刪除');
});

const fetchHistory = async () => {
  if (!user.value) return;
  historyError.value = '';
  const results = await Promise.allSettled([
    getUserBookings(user.value.google_id),
    getUserWorkOrders(user.value.google_id),
    getUser(user.value.google_id),
    getUserPoints(user.value.google_id),
    getUserPointTransactions(user.value.google_id)
  ]);

  const authFailure = results.find(result => {
    const status = result.status === 'rejected' ? result.reason?.response?.status : null;
    return status === 401 || status === 403;
  });
  if (authFailure) {
    authStore.logout();
    await router.replace('/login');
    return;
  }

  const [bookingResult, workOrderResult, userResult, pointResult, transactionResult] = results;
  if (bookingResult.status === 'fulfilled') bookings.value = bookingResult.value;
  if (workOrderResult.status === 'fulfilled') maintenanceRecords.value = workOrderResult.value;
  if (userResult.status === 'fulfilled') authStore.setUser(userResult.value);
  if (pointResult.status === 'fulfilled') pointSummary.value = pointResult.value;
  if (transactionResult.status === 'fulfilled') pointTransactions.value = transactionResult.value;

  if (results.some(result => result.status === 'rejected')) {
    historyError.value = '部分紀錄暫時無法載入，請稍後重新整理。';
    console.error('部分會員紀錄載入失敗:', results.filter(result => result.status === 'rejected'));
  }
};

const notifyVehicleDataUpdated = () => {
  localStorage.setItem(VEHICLE_DATA_UPDATED_KEY, String(Date.now()));
};

const refreshMemberData = () => {
  if (!user.value) return;
  fetchHistory();
  if (selectedVehicleMaintenance.value) {
    loadVehicleMaintenance(selectedVehicleMaintenance.value.motor);
  }
};

const handleVehicleStorageUpdate = (event) => {
  if (event.key === VEHICLE_DATA_UPDATED_KEY) refreshMemberData();
};

const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') refreshMemberData();
};

const formatNumber = (value) => Number(value || 0).toLocaleString();

const formatDateTime = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
};

const formatConsumptionDate = (value) => {
  if (!value) return '-';
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (match) return `${match[1]}/${match[2]}/${match[3]}`;
  return formatDateTime(value);
};

const lineItemAmount = (item) => Number(item.quantity || 0) * Number(item.unit_price || 0);

const workOrderItemNames = (record) => {
  const names = (record.line_items || []).map(item => `${item.name} x${item.quantity || 1}`);
  return names.length ? names.join('、') : '-';
};

const workOrderItemPrices = (record) => {
  const prices = (record.line_items || []).map(item => `NT$ ${formatNumber(lineItemAmount(item))}`);
  return prices.length ? prices.join('、') : '-';
};

const pointItemNames = (transaction) => {
  const names = (transaction.items || []).map(item => `${item.name} x${item.quantity || 1}`);
  return names.length ? names.join('、') : '-';
};

const formatPointChange = (points) => {
  const value = Number(points || 0);
  return value > 0 ? `+${value}` : String(value);
};

const openMaintenanceDetail = (record) => {
  selectedMaintenanceRecord.value = record;
};

const closeMaintenanceDetail = () => {
  selectedMaintenanceRecord.value = null;
};

const loadVehicleMaintenance = async (motor) => {
  vehicleMaintenanceLoading.value = true;
  vehicleMaintenanceError.value = '';
  try {
    const records = await getMotorMaintenanceRecords(motor.id || motor.ID);
    selectedVehicleMaintenance.value = { motor, records };
  } catch (error) {
    vehicleMaintenanceError.value = error.response?.data?.detail || '保養紀錄載入失敗，請稍後再試。';
  } finally {
    vehicleMaintenanceLoading.value = false;
  }
};

const openVehicleMaintenance = (motor) => {
  selectedVehicleMaintenance.value = { motor, records: [] };
  loadVehicleMaintenance(motor);
};

const closeVehicleMaintenance = () => {
  selectedVehicleMaintenance.value = null;
  vehicleMaintenanceError.value = '';
};

const vehicleMaintenanceItems = (record) => {
  const items = [];
  if (record.engine_oil) items.push('機油');
  if (record.gear_oil) items.push('齒輪油');
  if (record.air_filter) items.push('空氣濾清器');
  return items.length ? items.join('、') : '-';
};

const vehicleText = (record) => {
  const plate = record.vehicle_license_plate || '未記錄車牌';
  const model = [record.vehicle_brand, record.vehicle_model].filter(Boolean).join(' ');
  return model ? `${plate} / ${model}` : plate;
};

onMounted(() => {
  fetchHistory();
  window.addEventListener('storage', handleVehicleStorageUpdate);
  window.addEventListener('focus', refreshMemberData);
  document.addEventListener('visibilitychange', handleVisibilityChange);
});

onBeforeUnmount(() => {
  window.removeEventListener('storage', handleVehicleStorageUpdate);
  window.removeEventListener('focus', refreshMemberData);
  document.removeEventListener('visibilitychange', handleVisibilityChange);
});

watch(() => user.value, (newVal) => {
  if (newVal && bookings.value.length === 0) {
    fetchHistory();
  }
});


// =============== 基本資料 =================
const startEdit = () => {
  editForm.value = { 
    name: user.value.name, 
    phone: user.value.phone || ''
  };
  isEditing.value = true;
};

const saveProfile = async () => {
  try {
    await updateUserProfile(user.value.google_id, {
      name: editForm.value.name,
      phone: editForm.value.phone,
      motors: []
    });

    const refreshedUser = await getUser(user.value.google_id);
    authStore.setUser(refreshedUser);
    notifyVehicleDataUpdated();
    isEditing.value = false;
    alert('基本資料更新成功！');
  } catch (error) {
    console.error('更新資料失敗:', error);
    alert('更新基本資料失敗。');
  }
};

// =============== 愛車資料 (新增, 修改, 刪除) =================

const startAddMotor = () => {
  newMotorForm.value = { brand: '', model_name: '', license_plate: '', is_new_vehicle: false, purchase_date: '' };
  isAddingMotor.value = true;
};

const saveNewMotor = async () => {
  try {
    // 利用 updateUserProfile 將車輛加到陣列中，後端會判斷車牌不存在的話自動建立
    await updateUserProfile(user.value.google_id, {
      motors: [{
        ...newMotorForm.value,
        purchase_date: newMotorForm.value.purchase_date || null
      }]
    });
    
    const refreshedUser = await getUser(user.value.google_id);
    authStore.setUser(refreshedUser);
    notifyVehicleDataUpdated();
    
    isAddingMotor.value = false;
    alert('愛車新增成功！');
  } catch (error) {
    console.error('新增愛車失敗:', error);
    alert(error.response?.data?.detail || '愛車新增失敗，可能是車牌已被註冊。');
  }
};

const startEditMotor = (motor) => {
  editingMotorId.value = motor.id || motor.ID;
  editMotorForm.value = { 
    brand: motor.brand, 
    model_name: motor.model_name, 
    license_plate: motor.license_plate,
    is_new_vehicle: Boolean(motor.is_new_vehicle),
    purchase_date: motor.purchase_date || ''
  };
};

const saveEditMotor = async (motorId) => {
  try {
    await updateMotor(motorId, {
      ...editMotorForm.value,
      purchase_date: editMotorForm.value.purchase_date || null
    });
    
    const refreshedUser = await getUser(user.value.google_id);
    authStore.setUser(refreshedUser);
    notifyVehicleDataUpdated();
    
    editingMotorId.value = null;
    alert('愛車資料修改成功！');
  } catch (error) {
    console.error('愛車修改失敗:', error);
    alert('愛車修改失敗。');
  }
};

const deleteMotorHandler = async (motorId) => {
  if (!confirm('確定要刪除這台存入的愛車嗎？這個動作將無法復原。')) return;

  try {
    await deleteMotor(motorId);
    
    const refreshedUser = await getUser(user.value.google_id);
    authStore.setUser(refreshedUser);
    
    alert('愛車資料已刪除。');
  } catch (error) {
    console.error('刪除愛車失敗:', error);
    alert(error.response?.data?.detail || '刪除愛車失敗，請稍後再試。');
  }
};

// =============== 歷史紀錄 =================
const cancelBookingHandler = async (bookingId) => {
  if (!confirm('確定要取消這筆預約嗎？')) return;
  try {
    await updateBooking(bookingId, { status: 'CANCELED' });
    alert('預約已取消');
    await fetchHistory();
  } catch (error) {
    console.error('取消失敗:', error);
    alert('取消失敗，請稍後再試。');
  }
};
</script>

<style lang="scss" scoped>
@import '../assets/_variables.scss';

.member-center-page {
  padding: 2rem;
  max-width: 800px;
  margin: 2rem auto;

  h2 {
    color: $primary-light;
    text-align: center;
    margin-bottom: 0.5rem;
  }

  .subtitle {
    text-align: center;
    color: $text-secondary;
    margin-bottom: 2rem;
  }

  .profile-container {
    display: flex;
    flex-direction: column;
    gap: 2rem;

    .card {
      background-color: $dark-grey;
      border: 1px solid $medium-grey;
      border-radius: $border-radius;
      padding: 2rem;

      .header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid $medium-grey;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;

        h3 {
          color: $primary-color;
          margin: 0;
          border: none;
          padding: 0;
        }

        .btn-edit, .btn-primary-outline {
          background-color: transparent;
          color: $primary-light;
          border: 1px solid $primary-light;
          padding: 0.3rem 0.8rem;
          border-radius: $border-radius;
          cursor: pointer;
          transition: 0.3s;
          &:hover {
            background-color: rgba($primary-light, 0.1);
          }
        }
      }

      h3 {
        color: $primary-color;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid $medium-grey;
        padding-bottom: 0.5rem;
      }

      .info-group {
        display: flex;
        margin-bottom: 1rem;
        font-size: 1.1rem;

        .label {
          color: $light-grey;
          flex: 0 0 120px;
          font-weight: bold;
          white-space: nowrap;
        }

        .value {
          color: $text-primary;
        }
      }
    }

    .user-info-card {
      display: flex;
      gap: 2rem;
      flex-wrap: wrap;

      .avatar-section {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;

        .avatar-img {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          object-fit: cover;
          border: 2px solid $primary-color;
        }

        .d-none {
          display: none;
        }

        .btn-upload {
          background-color: $primary-color;
          color: $background-color;
          border: none;
          padding: 0.4rem 1rem;
          border-radius: $border-radius;
          cursor: pointer;
          &:hover {
            background-color: $primary-dark;
          }
        }
      }

      .info-details {
        flex: 1;
        min-width: 250px;
      }

      .edit-form {
        display: flex;
        flex-direction: column;
        gap: 1rem;

        .form-group {
          label {
            display: block;
            color: $light-grey;
            margin-bottom: 0.3rem;
          }
          input {
            width: 100%;
            padding: 0.5rem;
            border-radius: 4px;
            border: 1px solid $medium-grey;
            background: $background-color;
            color: $text-primary;
          }
        }

        .actions {
          display: flex;
          gap: 1rem;
          margin-top: 0.5rem;

          .btn-save {
            background-color: $primary-color;
            color: $background-color;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
          }

          .btn-cancel {
            background-color: transparent;
            color: $text-secondary;
            border: 1px solid $medium-grey;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
          }
        }
      }
    }

    .motors-card {
      .motor-table-wrap {
        overflow-x: auto;
        border: 1px solid $medium-grey;
        border-radius: 4px;
      }

      .motor-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;

        th,
        td {
          padding: 0.85rem 0.75rem;
          border-bottom: 1px solid $medium-grey;
          text-align: left;
          vertical-align: middle;
        }

        th {
          color: $text-secondary;
          font-size: 0.85rem;
          font-weight: 600;
        }

        tbody tr:last-child td {
          border-bottom: 0;
        }

        strong {
          color: $primary-light;
        }

        .motor-action-heading {
          width: 130px;
          text-align: right;
        }

        .maintenance-status {
          display: flex;
          flex-direction: column;
          gap: 0.15rem;

          small {
            color: $text-secondary;
          }
        }
      }

      .motor-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;

        .btn-text,
        .btn-text-danger {
          padding: 0.25rem;
          border: 0;
          background: none;
          cursor: pointer;
          text-decoration: underline;
        }

        .btn-text {
          color: $primary-light;
        }

        .btn-text-danger {
          color: #ff6b6b;
        }
      }

      .motor-edit-row td {
        padding: 1rem;
        background: rgba(255, 255, 255, 0.02);
      }

      .motor-form {
        display: flex;
        flex-direction: column;
        gap: 1rem;

        .motor-edit-fields {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.5rem;

          input {
            min-width: 0;
            padding: 0.5rem;
            border-radius: 4px;
            border: 1px solid $medium-grey;
            background: $background-color;
            color: $text-primary;
          }

          .new-vehicle-toggle {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            min-height: 38px;
            color: $text-secondary;

            input {
              width: 18px;
              height: 18px;
            }
          }
        }

        .actions {
          display: flex;
          gap: 1rem;

          .btn-save {
            background-color: $primary-color;
            color: $background-color;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
          }

          .btn-cancel {
            background-color: transparent;
            color: $text-secondary;
            border: 1px solid $medium-grey;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
          }
        }
      }

      .new-motor-form {
        margin-bottom: 1.5rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid $medium-grey;
      }

      .no-motors {
        color: $text-disabled;
        text-align: center;
        padding: 2rem 0;
      }
    }
    
    .history-section {
      background-color: $dark-grey;
      border: 1px solid $medium-grey;
      border-radius: $border-radius;
      overflow: hidden;

      .tabs {
        display: flex;
        border-bottom: 1px solid $medium-grey;
        
        button {
          flex: 1;
          background: transparent;
          border: none;
          padding: 1rem;
          color: $text-secondary;
          cursor: pointer;
          font-size: 1.1rem;
          font-weight: bold;
          transition: all 0.3s ease;

          &:hover {
            color: $text-primary;
            background: rgba(255,255,255,0.02);
          }

          &.active {
            color: $primary-color;
            border-bottom: 3px solid $primary-color;
          }
        }
      }

      .history-error {
        margin: 1rem 2rem 0;
        padding: 0.75rem 1rem;
        border-left: 3px solid $primary-color;
        color: $text-primary;
        background: rgba(255, 71, 71, 0.08);
      }

      .tab-content {
        padding: 2rem;

        .history-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;

          .history-item {
            background-color: $background-color;
            border-radius: $border-radius;
            padding: 1rem;
            
            .item-header {
              display: flex;
              justify-content: space-between;
              border-bottom: 1px solid $medium-grey;
              padding-bottom: 0.5rem;
              margin-bottom: 0.5rem;
            }

            .item-body {
              p {
                margin: 0.35rem 0;
              }
            }

            .maintenance-lines {
              display: grid;
              gap: 0.5rem;
              margin: 0.85rem 0;
            }

            .maintenance-line {
              display: grid;
              grid-template-columns: 120px minmax(0, 1fr);
              gap: 0.35rem 0.75rem;
              padding: 0.75rem;
              border: 1px solid $medium-grey;
              border-radius: $border-radius;
              background: rgba(255, 255, 255, 0.03);

              span,
              small {
                color: $text-secondary;
              }

              strong {
                color: $text-primary;
              }

              small {
                grid-column: 2;
              }
            }
          }
        }

        .empty-state {
          text-align: center;
          color: $text-disabled;
          padding: 2rem;
        }
      }
      
      .btn-new-booking {
        background-color: $primary-color;
        color: $background-color;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: $border-radius;
        font-weight: bold;
        cursor: pointer;
        transition: background-color 0.3s;
        &:hover {
          background-color: $primary-dark;
        }
      }
      
      .btn-cancel-booking {
        margin-top: 1rem;
        background-color: transparent;
        color: #ff6b6b;
        border: 1px solid #ff6b6b;
        padding: 0.4rem 0.8rem;
        border-radius: $border-radius;
        cursor: pointer;
        transition: all 0.3s;

        &:hover {
          background-color: rgba(#ff6b6b, 0.1);
        }
      }
    }

    .record-table-wrap {
      width: 100%;
      overflow-x: auto;
    }

    .record-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;

      th,
      td {
        padding: 0.85rem 0.75rem;
        border-bottom: 1px solid $medium-grey;
        text-align: left;
        vertical-align: top;
      }

      th {
        color: $text-secondary;
        font-weight: 600;
        white-space: nowrap;
      }

      td {
        color: $text-primary;
      }

      td > strong,
      td > small {
        display: block;
      }

      td > small {
        margin-top: 0.25rem;
        color: $text-secondary;
      }

      tbody tr:last-child td {
        border-bottom: 0;
      }

      .amount-cell,
      .points-cell {
        white-space: nowrap;
        font-weight: 700;
      }

      .points-cell.positive {
        color: #63c88f;
      }

      .points-cell.negative {
        color: #ff7d7d;
      }

      .action-cell {
        text-align: right;
        white-space: nowrap;
      }
    }

    .btn-record-detail {
      min-height: 36px;
      padding: 0.45rem 0.75rem;
      border: 1px solid $primary-color;
      border-radius: 4px;
      background: transparent;
      color: $primary-color;
      cursor: pointer;

      &:hover {
        background: rgba($primary-color, 0.1);
      }
    }

    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }

    .record-modal-overlay {
      position: fixed;
      inset: 0;
      z-index: 1000;
      display: grid;
      place-items: center;
      padding: 1rem;
      background: rgba(0, 0, 0, 0.72);
    }

    .record-modal {
      width: min(920px, 100%);
      max-height: calc(100vh - 2rem);
      box-sizing: border-box;
      overflow-y: auto;
      padding: 1.25rem;
      border: 1px solid $medium-grey;
      border-radius: 6px;
      background: $dark-grey;
      box-shadow: 0 18px 48px rgba(0, 0, 0, 0.35);
    }

    .record-modal-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 1rem;

      h2,
      p {
        margin: 0;
      }

      p {
        margin-top: 0.3rem;
        color: $text-secondary;
      }
    }

    .record-modal-close {
      width: 38px;
      height: 38px;
      flex: 0 0 38px;
      border: 0;
      border-radius: 4px;
      background: transparent;
      color: $text-primary;
      font-size: 1.6rem;
      cursor: pointer;

      &:hover {
        background: rgba(255, 255, 255, 0.08);
      }
    }

    .record-summary {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      margin: 0 0 1rem;
      border-top: 1px solid $medium-grey;
      border-bottom: 1px solid $medium-grey;

      div {
        padding: 0.85rem 0.65rem;
      }

      dt {
        color: $text-secondary;
        font-size: 0.82rem;
      }

      dd {
        margin: 0.25rem 0 0;
        color: $text-primary;
      }
    }

    .record-notes {
      display: grid;
      gap: 0.75rem;
      margin-bottom: 1rem;

      p {
        margin: 0;
      }

      strong {
        display: block;
        margin-bottom: 0.2rem;
        color: $text-secondary;
      }
    }

    .record-total {
      display: flex;
      justify-content: flex-end;
      align-items: baseline;
      gap: 0.75rem;
      padding-top: 1rem;
      font-size: 1rem;

      strong {
        color: $primary-color;
        font-size: 1.2rem;
      }
    }

    @media (max-width: 760px) {
      .motors-card .motor-form .motor-edit-fields {
        grid-template-columns: 1fr;
      }

      .motors-card {
        .motor-table-wrap {
          overflow: visible;
        }

        .motor-table {
          table-layout: auto;

          thead {
            display: none;
          }

          tbody,
          tr,
          td {
            display: block;
            width: 100%;
          }

          tr {
            padding: 0.65rem 0;
            border-bottom: 1px solid $medium-grey;
          }

          tr:last-child {
            border-bottom: 0;
          }

          td {
            display: grid;
            grid-template-columns: 100px minmax(0, 1fr);
            gap: 0.75rem;
            padding: 0.4rem 0.75rem;
            border: 0;
          }

          td::before {
            content: attr(data-label);
            color: $text-secondary;
            font-weight: 600;
          }

          .motor-actions {
            display: flex;
            justify-content: flex-start;
            padding-left: calc(100px + 1.5rem);
          }

          .motor-actions::before,
          .motor-edit-row td::before {
            content: none;
          }

          .motor-edit-row {
            padding: 0;
          }

          .motor-edit-row td {
            display: block;
            padding: 1rem;
          }
        }
      }

      .history-section .tabs button {
        padding: 0.8rem 0.45rem;
        font-size: 0.9rem;
      }

      .history-section .tab-content {
        padding: 1rem;
      }

      .record-table {
        thead {
          display: none;
        }

        tbody,
        tr,
        td {
          display: block;
          width: 100%;
        }

        tr {
          padding: 0.75rem 0;
          border-bottom: 1px solid $medium-grey;
        }

        tr:last-child {
          border-bottom: 0;
        }

        td {
          display: grid;
          grid-template-columns: minmax(90px, 34%) minmax(0, 1fr);
          gap: 0.75rem;
          padding: 0.4rem 0;
          border: 0;
        }

        td::before {
          content: attr(data-label);
          color: $text-secondary;
          font-weight: 600;
        }

        .action-cell {
          display: block;
          padding-top: 0.7rem;
          text-align: left;
        }

        .action-cell::before {
          content: none;
        }

        .btn-record-detail {
          width: 100%;
        }
      }

      .record-summary {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .record-modal {
        padding: 1rem;
      }
    }
  }

  .loading {
    text-align: center;
    color: $text-secondary;
  }
}
</style>
