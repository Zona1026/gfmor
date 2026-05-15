<template>
  <div class="member-center-page">
    <h2>會員中心</h2>
    <p class="subtitle">歡迎回來，{{ user?.name }}！以下是您的個人與車輛資訊。</p>
    
    <div v-if="user" class="profile-container">
      <!-- 頭像與基本資料 -->
      <div class="card user-info-card">
        <div class="avatar-section">
          <!-- Fallback path needs to be correct, maybe an SVG or default icon -->
          <img :src="user.avatar || 'https://via.placeholder.com/120?text=Avatar'" alt="會員頭像" class="avatar-img" />
          <input type="file" ref="fileInput" @change="handleAvatarChange" accept="image/*" class="d-none" />
          <button @click="$refs.fileInput.click()" class="btn-upload">更換頭像</button>
        </div>

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
        <form v-if="isAddingMotor" @submit.prevent="saveNewMotor" class="motor-form motor-item new-motor-form">
          <h4 style="margin-bottom: 1rem; color: #fff;">新增車輛</h4>
          <div class="motor-edit-fields">
            <input v-model="newMotorForm.brand" placeholder="廠牌 (如 YAMAHA)" required />
            <input v-model="newMotorForm.model_name" placeholder="型號 (如 勁戰六代)" required />
            <input v-model="newMotorForm.license_plate" placeholder="車牌 (如 ABC-1234)" required />
          </div>
          <div class="actions">
            <button type="submit" class="btn-save">儲存新增</button>
            <button type="button" @click="isAddingMotor = false" class="btn-cancel">取消</button>
          </div>
        </form>

        <div v-if="completeMotors && completeMotors.length > 0" class="motors-list">
          <div v-for="motor in completeMotors" :key="motor.license_plate" class="motor-item">
            
            <!-- 單一車輛的顯示模式 -->
            <div v-if="editingMotorId !== (motor.id || motor.ID)">
              <div class="motor-detail">
                <span class="label">廠牌：</span>
                <span class="value">{{ motor.brand }}</span>
              </div>
              <div class="motor-detail">
                <span class="label">型號：</span>
                <span class="value">{{ motor.model_name }}</span>
              </div>
              <div class="motor-detail">
                <span class="label">車牌號碼：</span>
                <span class="value">{{ motor.license_plate }}</span>
              </div>
              <div class="motor-actions">
                <button @click="startEditMotor(motor)" class="btn-text">編輯</button>
                <button @click="deleteMotorHandler(motor.id || motor.ID)" class="btn-text-danger">刪除</button>
              </div>
            </div>

            <!-- 單一車輛的編輯模式 -->
            <form v-else @submit.prevent="saveEditMotor(motor.id || motor.ID)" class="motor-form">
               <div class="motor-edit-fields">
                 <input v-model="editMotorForm.brand" placeholder="廠牌" required />
                 <input v-model="editMotorForm.model_name" placeholder="型號" required />
                 <input v-model="editMotorForm.license_plate" placeholder="車牌" required />
               </div>
               <div class="actions">
                 <button type="submit" class="btn-save">儲存修改</button>
                 <button type="button" @click="editingMotorId = null" class="btn-cancel">取消</button>
               </div>
            </form>

          </div>
        </div>
        <p v-else-if="!isAddingMotor" class="no-motors">目前尚未登錄任何完整車輛資訊。</p>
      </div>

      <!-- 歷史紀錄 -->
      <div class="history-section">
        <div class="tabs">
          <button :class="{ active: activeTab === 'bookings' }" @click="activeTab = 'bookings'">預約紀錄</button>
          <button :class="{ active: activeTab === 'orders' }" @click="activeTab = 'orders'">消費紀錄</button>
        </div>

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

        <div v-if="activeTab === 'orders'" class="tab-content">
          <div v-if="orders.length > 0" class="history-list">
            <div v-for="order in orders" :key="order.id" class="history-item">
              <div class="item-header">
                <strong>訂單編號: #{{ order.id }}</strong>
                <span class="status">{{ orderStatusMap[order.status] || order.status }}</span>
              </div>
              <div class="item-body">
                <p>時間: {{ new Date(order.created_at).toLocaleString() }}</p>
                <p>金額: ${{ order.total_amount }}</p>
              </div>
            </div>
          </div>
          <p v-else class="empty-state">尚無消費紀錄</p>
        </div>
      </div>

    </div>
    <div v-else class="loading">
      載入中或尚未登入...
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useAuthStore } from '../store/auth';
import { uploadAvatar, updateUserProfile, getUser } from '../api/users';
import { getUserBookings, updateBooking } from '../api/bookings';
import { getUserOrders } from '../api/orders';
import { updateMotor, deleteMotor } from '../api/motors';

const router = useRouter();
const authStore = useAuthStore();
const { user } = storeToRefs(authStore);

const activeTab = ref('bookings');
const bookings = ref([]);
const orders = ref([]);

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

const orderStatusMap = {
  'PENDING': '未付款',
  'DEPOSIT_PAID': '已付訂金',
  'FULL_PAID': '已付全款',
  'COMPLETED': '已結案',
  'CANCELED': '已取消'
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

// Basic profile editing
const isEditing = ref(false);
const editForm = ref({ name: '', phone: '' });

// Motor editing & creating
const isAddingMotor = ref(false);
const newMotorForm = ref({ brand: '', model_name: '', license_plate: '' });
const editingMotorId = ref(null);
const editMotorForm = ref({ brand: '', model_name: '', license_plate: '' });

const fileInput = ref(null);

const completeMotors = computed(() => {
  if (!user.value || !user.value.motors) return [];
  // 過濾未被軟刪除的車輛 (通常後端過濾了，但保險起見也可在這裡過濾)
  return user.value.motors.filter(m => m.brand && m.model_name && m.license_plate && m.status !== '已刪除');
});

const fetchHistory = async () => {
  if (!user.value) return;
  try {
    const [bRes, oRes, uRes] = await Promise.all([
      getUserBookings(user.value.google_id),
      getUserOrders(user.value.google_id),
      getUser(user.value.google_id)
    ]);
    bookings.value = bRes;
    orders.value = oRes;
    // 同步最新的會員資料（如累積消費）
    authStore.setUser(uRes);
  } catch (error) {
    console.error('取得紀錄失敗:', error);
  }
};

onMounted(() => {
  fetchHistory();
});

watch(() => user.value, (newVal) => {
  if (newVal && bookings.value.length === 0) {
    fetchHistory();
  }
});

const handleAvatarChange = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const updatedUser = await uploadAvatar(user.value.google_id, formData);
    authStore.setUser(updatedUser);
  } catch (error) {
    console.error('上傳頭像失敗:', error);
    alert('頭像上傳失敗，請檢查網路狀態或圖片大小。');
  }
};

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
    isEditing.value = false;
    alert('基本資料更新成功！');
  } catch (error) {
    console.error('更新資料失敗:', error);
    alert('更新基本資料失敗。');
  }
};

// =============== 愛車資料 (新增, 修改, 刪除) =================

const startAddMotor = () => {
  newMotorForm.value = { brand: '', model_name: '', license_plate: '' };
  isAddingMotor.value = true;
};

const saveNewMotor = async () => {
  try {
    // 利用 updateUserProfile 將車輛加到陣列中，後端會判斷車牌不存在的話自動建立
    await updateUserProfile(user.value.google_id, {
      motors: [newMotorForm.value]
    });
    
    const refreshedUser = await getUser(user.value.google_id);
    authStore.setUser(refreshedUser);
    
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
    license_plate: motor.license_plate 
  };
};

const saveEditMotor = async (motorId) => {
  try {
    await updateMotor(motorId, editMotorForm.value);
    
    const refreshedUser = await getUser(user.value.google_id);
    authStore.setUser(refreshedUser);
    
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
          width: 100px;
          font-weight: bold;
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
      .motors-list {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
      }

      .motor-item {
        background-color: $background-color;
        padding: 1.5rem;
        border-radius: $border-radius;
        border-left: 4px solid $primary-light;

        .motor-detail {
          display: flex;
          margin-bottom: 0.5rem;
          
          &:last-child {
            margin-bottom: 0;
          }

          .label {
            color: $light-grey;
            width: 100px;
            font-weight: bold;
          }

          .value {
            color: $text-primary;
          }
        }

        .motor-actions {
          display: flex;
          gap: 1rem;
          margin-top: 1rem;

          .btn-text {
            background: none;
            border: none;
            color: $primary-light;
            cursor: pointer;
            text-decoration: underline;
          }
          
          .btn-text-danger {
            background: none;
            border: none;
            color: #ff6b6b;
            cursor: pointer;
            text-decoration: underline;
          }
        }
      }

      .motor-form {
        display: flex;
        flex-direction: column;
        gap: 1rem;

        .motor-edit-fields {
          display: flex;
          gap: 0.5rem;
          input {
            flex: 1;
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
  }

  .loading {
    text-align: center;
    color: $text-secondary;
  }
}
</style>
