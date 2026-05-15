<template>
  <div class="datepicker-wrapper" ref="wrapperRef">
    <div class="date-input" @click="toggleCalendar" :class="{ 'has-value': !!modelValue }">
      <span v-if="modelValue" class="formatted-value">{{ formattedDate }}</span>
      <span v-else class="placeholder">請選擇日期...</span>
      <span class="icon">📅</span>
    </div>

    <div class="calendar-popup" v-if="isOpen">
      <div class="custom-datepicker">
        <div class="calendar-header">
          <button type="button" class="btn-nav" @click.prevent="prevMonth">&lt;</button>
          <span class="month-title">{{ currentYear }} 年 {{ currentMonth + 1 }} 月</span>
          <button type="button" class="btn-nav" @click.prevent="nextMonth">&gt;</button>
        </div>
        
        <div class="calendar-grid">
          <div class="weekday holiday">日</div>
          <div class="weekday">一</div>
          <div class="weekday">二</div>
          <div class="weekday">三</div>
          <div class="weekday">四</div>
          <div class="weekday">五</div>
          <div class="weekday holiday">六</div>
          
          <div 
            v-for="(day, index) in calendarDays" 
            :key="index"
            class="day"
            :class="{ 
              'empty': !day.date, 
              'disabled': day.disabled, 
              'selected': modelValue === day.date,
              'today': day.isToday
            }"
            @click="selectDate(day)">
            <span v-if="day.date">{{ day.dayNum }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  modelValue: {
    type: String, // 'YYYY-MM-DD'
    default: ''
  },
  minDate: {
    type: String, // 'YYYY-MM-DD'
    default: ''
  }
});

const emit = defineEmits(['update:modelValue', 'change']);

const wrapperRef = ref(null);
const isOpen = ref(false);

const toggleCalendar = () => {
  isOpen.value = !isOpen.value;
};

// 點擊外部關閉日曆
const handleClickOutside = (event) => {
  if (wrapperRef.value && !wrapperRef.value.contains(event.target)) {
    isOpen.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

const formattedDate = computed(() => {
  if (!props.modelValue) return '';
  const d = new Date(props.modelValue);
  return `${d.getFullYear()}年${String(d.getMonth() + 1).padStart(2, '0')}月${String(d.getDate()).padStart(2, '0')}日`;
});

// Initialize with current month or selected date's month
const initialDate = props.modelValue ? new Date(props.modelValue) : new Date();
const currentYear = ref(initialDate.getFullYear());
const currentMonth = ref(initialDate.getMonth()); // 0-11

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    const d = new Date(newVal);
    currentYear.value = d.getFullYear();
    currentMonth.value = d.getMonth();
  }
});

const prevMonth = () => {
  if (currentMonth.value === 0) {
    currentMonth.value = 11;
    currentYear.value -= 1;
  } else {
    currentMonth.value -= 1;
  }
};

const nextMonth = () => {
  if (currentMonth.value === 11) {
    currentMonth.value = 0;
    currentYear.value += 1;
  } else {
    currentMonth.value += 1;
  }
};

const getIsoDateString = (year, month, day) => {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
};

const getTodayIsoString = () => {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().split('T')[0];
};

const todayStr = getTodayIsoString();

const calendarDays = computed(() => {
  const days = [];
  const firstDayOfMonth = new Date(currentYear.value, currentMonth.value, 1).getDay();
  const daysInMonth = new Date(currentYear.value, currentMonth.value + 1, 0).getDate();
  
  // Fill empty slots before the 1st of the month
  for (let i = 0; i < firstDayOfMonth; i++) {
    days.push({ date: null });
  }
  
  for (let i = 1; i <= daysInMonth; i++) {
    const dateStr = getIsoDateString(currentYear.value, currentMonth.value, i);
    let disabled = false;
    
    if (props.minDate && dateStr < props.minDate) {
      disabled = true;
    }
    
    // Disable Sundays completely based on business rule
    const isSunday = new Date(currentYear.value, currentMonth.value, i).getDay() === 0;
    if (isSunday) {
      disabled = true;
    }
    
    days.push({
      date: dateStr,
      dayNum: i,
      disabled,
      isToday: dateStr === todayStr
    });
  }
  
  return days;
});

const selectDate = (day) => {
  if (!day.date || day.disabled) return;
  emit('update:modelValue', day.date);
  emit('change', day.date);
  isOpen.value = false; // 選擇後自動關閉
};
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.datepicker-wrapper {
  position: relative;
  width: 100%;

  .date-input {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.8rem;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    background-color: $background-color;
    cursor: pointer;
    color: $text-primary;
    transition: border-color 0.3s;

    &:hover {
      border-color: $primary-light;
    }

    .placeholder {
      color: $text-disabled;
    }

    .formatted-value {
      font-weight: 500;
      color: $primary-light;
    }

    .icon {
      opacity: 0.8;
    }
  }

  .calendar-popup {
    position: absolute;
    top: calc(100% + 5px);
    left: 0;
    z-index: 1000;
    min-width: 320px;
    width: 100%;
  }
}

.custom-datepicker {
  background-color: $dark-grey;
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  padding: 1rem;
  width: 100%;
  max-width: 350px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.3);

  .calendar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;

    .month-title {
      color: $primary-light;
      font-weight: bold;
      font-size: 1.1rem;
    }

    .btn-nav {
      background: $medium-grey;
      border: none;
      color: $text-primary;
      padding: 0.3rem 0.8rem;
      border-radius: 4px;
      cursor: pointer;
      font-weight: bold;
      
      &:hover {
        background: $primary-color;
      }
    }
  }

  .calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 0.5rem;
    text-align: center;

    .weekday {
      font-size: 0.85rem;
      color: $text-secondary;
      margin-bottom: 0.5rem;
      &.holiday {
        color: #ff6b6b;
      }
    }

    .day {
      display: flex;
      justify-content: center;
      align-items: center;
      aspect-ratio: 1;
      border-radius: 50%;
      cursor: pointer;
      font-size: 0.95rem;
      transition: all 0.2s;

      &:not(.empty):not(.disabled):hover {
        background-color: rgba($primary-light, 0.2);
        color: $primary-light;
      }

      &.empty {
        background: transparent;
        cursor: default;
      }

      &.disabled {
        color: $medium-grey;
        cursor: not-allowed;
        background-color: transparent;
      }

      &.today {
        border: 1px solid $medium-grey;
      }

      &.selected {
        background-color: $primary-color !important;
        color: white !important;
        font-weight: bold;
        box-shadow: 0 0 8px rgba($primary-color, 0.6);
      }
    }
  }
}
</style>
