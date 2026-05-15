<template>
  <div class="booking-page">
    <h2>線上預約</h2>
    <div class="booking-container">
      <form @submit.prevent="submitBooking" class="booking-form">
        <!-- 選擇愛車 -->
        <div class="form-group">
          <label>選擇愛車</label>
          <select v-model="form.motor_id" required>
            <option value="" disabled>請選擇要服務的車輛</option>
            <option v-for="motor in completeMotors" :key="motor.id || motor.ID" :value="motor.id || motor.ID">
              {{ motor.brand }} {{ motor.model_name }} ({{ motor.license_plate }})
            </option>
          </select>
          <small v-if="completeMotors.length === 0" class="error-text">請先至會員中心新增完整的愛車資訊</small>
        </div>

        <!-- 服務類別 -->
        <div class="form-group">
          <label>服務類別</label>
          <select v-model="form.category" required>
            <option value="" disabled>請選擇服務類別</option>
            <option value="MAINTENANCE">保養</option>
            <option value="REPAIR">維修</option>
            <option value="CONSULTATION">諮詢</option>
          </select>
        </div>

        <!-- 選擇日期（日曆元件） -->
        <div class="form-group">
          <label>預約日期</label>
          <DatePicker v-model="form.date" :minDate="minDate" @change="onDateChange" />
          <small class="info-text">營業時間：週一至週五 13:00~22:00，週六 11:00~22:00，週日公休。</small>
        </div>

        <!-- 選擇時間 -->
        <div class="form-group" v-if="form.date">
          <label>預約時段</label>
          <div v-if="isSunday" class="error-text">週日公休，請選擇其他日期</div>
          <div v-else-if="availableTimeSlots.length === 0" class="error-text">該日已無可預約時段，請選擇其他日期</div>
          <select v-else v-model="form.time" required>
            <option value="" disabled>請選擇時間（每半小時為一時段）</option>
            <option v-for="slot in availableTimeSlots" :key="slot.value" :value="slot.value" :disabled="slot.disabled">
              {{ slot.label }} {{ slot.disabled ? '(無法預約)' : '' }}
            </option>
          </select>
        </div>

        <!-- 備註 -->
        <div class="form-group">
          <label>備註 (選填)</label>
          <textarea v-model="form.notes" rows="4" placeholder="請簡述您的需求..."></textarea>
        </div>

        <button type="submit" class="btn-submit" :disabled="!isFormValid || isSubmitting">
          {{ isSubmitting ? '預約中...' : '確認預約' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../store/auth';
import { storeToRefs } from 'pinia';
import { createBooking, getDailyBookings } from '../api/bookings';
import DatePicker from '../components/common/DatePicker.vue';

const router = useRouter();
const authStore = useAuthStore();
const { user } = storeToRefs(authStore);

const form = ref({
  motor_id: '',
  category: '',
  date: '',
  time: '',
  notes: ''
});

const isSubmitting = ref(false);
const occupiedSlots = ref([]);
const isSunday = ref(false);

const completeMotors = computed(() => {
  if (!user.value || !user.value.motors) return [];
  return user.value.motors.filter(m => m.brand && m.model_name && m.license_plate);
});

// 設定最小可選日期為今天 (本地時間)
const minDate = computed(() => {
  const currentZoneDate = new Date();
  const offset = currentZoneDate.getTimezoneOffset() * 60000;
  const localIsoTime = new Date(currentZoneDate.getTime() - offset).toISOString().split('T')[0];
  return localIsoTime;
});

const isFormValid = computed(() => {
  return form.value.motor_id && form.value.category && form.value.date && form.value.time && !isSunday.value;
});

const onDateChange = async () => {
  form.value.time = '';
  occupiedSlots.value = [];
  
  if (!form.value.date) return;
  
  const selectedDate = new Date(form.value.date);
  isSunday.value = selectedDate.getDay() === 0;

  if (isSunday.value) return;

  try {
    const records = await getDailyBookings(form.value.date);
    // records 包含該日所有 PENDING 預約。將 booking_time 取出 HH:mm
    occupiedSlots.value = records.map(b => {
      const dt = new Date(b.booking_time);
      return `${dt.getHours().toString().padStart(2, '0')}:${dt.getMinutes().toString().padStart(2, '0')}`;
    });
  } catch (err) {
    console.error("無法取得該日預約狀況", err);
  }
};

const availableTimeSlots = computed(() => {
  if (!form.value.date || isSunday.value) return [];
  
  const selectedDate = new Date(form.value.date);
  const dayOfWeek = selectedDate.getDay();
  let startHour = 13;
  let endHour = 21; // Last slot starts at 21:00

  if (dayOfWeek === 6) { // Saturday
    startHour = 11;
  }

  const slots = [];
  const now = new Date();
  // 修正: 使用更精確的時區處理
  const isToday = form.value.date === new Date().toLocaleDateString('en-CA');
  const currentMins = now.getHours() * 60 + now.getMinutes();

  for (let h = startHour; h <= endHour; h++) {
    // 00 分時段
    const slot1TimeStr = `${h.toString().padStart(2, '0')}:00`;
    const slot1Mins = h * 60;
    const isPast1 = isToday && (slot1Mins <= currentMins);
    slots.push({
      value: slot1TimeStr,
      label: slot1TimeStr,
      disabled: isPast1 || occupiedSlots.value.includes(slot1TimeStr)
    });

    // 30 分時段 (除了最後一個小時的結束時間以外)
    if (h !== endHour) {
      const slot2TimeStr = `${h.toString().padStart(2, '0')}:30`;
      const slot2Mins = h * 60 + 30;
      const isPast2 = isToday && (slot2Mins <= currentMins);
      slots.push({
        value: slot2TimeStr,
        label: slot2TimeStr,
        disabled: isPast2 || occupiedSlots.value.includes(slot2TimeStr)
      });
    }
  }
  return slots;
});

const submitBooking = async () => {
  if (!isFormValid.value) return;
  isSubmitting.value = true;
  
  try {
    // We compose the datetime string. Note: backend might expect ISO 8601 without timezone
    // e.g. "2026-03-26T14:00:00"
    const bookingTimeStr = `${form.value.date}T${form.value.time}:00`;
    
    await createBooking({
      google_id: user.value.google_id,
      motor_id: form.value.motor_id,
      booking_time: bookingTimeStr,
      category: form.value.category,
      notes: form.value.notes || null
    });
    
    alert('預約成功！');
    router.push('/profile');
  } catch (error) {
    console.error(error);
    alert(error.response?.data?.detail || '預約失敗，請稍後再試。');
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style lang="scss" scoped>
@import '../assets/_variables.scss';

.booking-page {
  padding: 2rem;
  max-width: 600px;
  margin: 2rem auto;

  h2 {
    color: $primary-light;
    text-align: center;
    margin-bottom: 2rem;
  }

  .booking-container {
    background-color: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    padding: 2.5rem;
  }

  .booking-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;

      label {
        color: $light-grey;
        font-weight: bold;
      }

      select, input, textarea {
        padding: 0.8rem;
        background-color: $background-color;
        border: 1px solid $medium-grey;
        border-radius: 4px;
        color: $text-primary;
        font-size: 1rem;

        &:focus {
          outline: none;
          border-color: $primary-color;
        }

        &[disabled] {
          opacity: 0.6;
          cursor: not-allowed;
          background-color: rgba($light-grey, 0.1);
        }
      }

      .info-text {
        color: $text-secondary;
        font-size: 0.85rem;
        margin-top: 0.2rem;
      }

      .error-text {
        color: #ff6b6b;
        font-size: 0.85rem;
        margin-top: 0.2rem;
      }
    }

    .btn-submit {
      margin-top: 1rem;
      background-color: $primary-color;
      color: $background-color;
      border: none;
      padding: 1rem;
      font-size: 1.1rem;
      font-weight: bold;
      border-radius: $border-radius;
      cursor: pointer;
      transition: background-color 0.3s;

      &:hover:not(:disabled) {
        background-color: $primary-dark;
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }
  }
}
</style>
