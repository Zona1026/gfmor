<template>
  <div class="checkout-page">
    <h2>確認訂單</h2>

    <div class="checkout-layout">
      <!-- 訂單明細 -->
      <div class="order-summary">
        <h3>訂單明細</h3>
        <div v-for="item in cartItems" :key="item.product_id" class="summary-item">
          <span class="item-name">{{ item.name }} × {{ item.quantity }}</span>
          <span class="item-total">NT$ {{ (item.price * item.quantity).toLocaleString() }}</span>
        </div>
        <div class="summary-total">
          <strong>合計</strong>
          <strong class="total-amount">NT$ {{ cartStore.totalAmount.toLocaleString() }}</strong>
        </div>
      </div>

      <!-- 訂購人資訊（自動帶入） -->
      <div class="checkout-form">
        <h3>訂購人資訊</h3>
        <div class="info-row">
          <label>姓名</label>
          <span>{{ user?.name || '—' }}</span>
        </div>
        <div class="info-row">
          <label>電話</label>
          <span>{{ user?.phone || '—' }}</span>
        </div>

        <p class="payment-note">
          💡 訂單送出後將跳轉至 LINE 官方帳號，由店家與您聯繫付款及取貨事宜。
        </p>

        <button class="btn-submit" :disabled="submitting || cartItems.length === 0" @click="handleSubmitOrder">
          {{ submitting ? '送出中...' : '送出訂單' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useCartStore } from '../store/cart';
import { useAuthStore } from '../store/auth';
import api from '../api/index';

const cartStore = useCartStore();
const authStore = useAuthStore();
const { items: cartItems } = storeToRefs(cartStore);
const { user } = storeToRefs(authStore);

const submitting = ref(false);

const handleSubmitOrder = async () => {
  if (!user.value) {
    alert('請先登入後再結帳');
    return;
  }
  if (cartItems.value.length === 0) {
    alert('購物車是空的');
    return;
  }

  submitting.value = true;
  try {
    const orderData = {
      google_id: user.value.google_id,
      total_amount: cartStore.totalAmount,
      recipient_name: user.value.name || '',
      recipient_phone: user.value.phone || '',
      shipping_address: '店取',
      notes: '',
      items: cartItems.value.map(i => ({
        product_id: i.product_id,
        quantity: i.quantity,
        unit_price: i.price
      }))
    };

    await api.post('/orders/', orderData);
    cartStore.clearCart();
    alert('訂單已成功送出！即將跳轉至 LINE 官方帳號。');
    // 跳轉到 LINE 官方帳號
    window.location.href = 'https://lin.ee/23mk4EM';
  } catch (e) {
    console.error(e);
    alert('訂單送出失敗：' + (e.response?.data?.detail || '請稍後再試'));
  } finally {
    submitting.value = false;
  }
};
</script>

<style lang="scss" scoped>
@import '../assets/_variables.scss';

.checkout-page {
  padding: 2rem;
  max-width: 800px;
  margin: 1rem auto;

  h2 { color: $primary-light; text-align: center; margin-bottom: 1.5rem; }

  .checkout-layout {
    display: flex; flex-direction: column; gap: 1.5rem;
  }

  .order-summary {
    background: $dark-grey; border: 1px solid $medium-grey; border-radius: 8px; padding: 1.5rem;

    h3 { color: $primary-light; margin: 0 0 1rem; border-bottom: 1px solid $medium-grey; padding-bottom: 0.8rem; }

    .summary-item {
      display: flex; justify-content: space-between; padding: 0.5rem 0;
      color: $text-secondary; border-bottom: 1px solid rgba($medium-grey, 0.3);
      .item-total { color: $text-primary; }
    }

    .summary-total {
      display: flex; justify-content: space-between; padding: 1rem 0 0;
      font-size: 1.1rem; color: $text-primary;
      .total-amount { color: $primary-light; font-size: 1.3rem; }
    }
  }

  .checkout-form {
    background: $dark-grey; border: 1px solid $medium-grey; border-radius: 8px; padding: 1.5rem;

    h3 { color: $primary-light; margin: 0 0 1rem; border-bottom: 1px solid $medium-grey; padding-bottom: 0.8rem; }

    .info-row {
      display: flex; align-items: center; gap: 1rem; padding: 0.6rem 0;
      border-bottom: 1px solid rgba($medium-grey, 0.3);
      label { color: $text-disabled; font-weight: 600; min-width: 50px; }
      span { color: $text-primary; font-size: 1rem; }
    }

    .payment-note {
      color: $text-disabled; font-size: 0.85rem; background: rgba($primary-color, 0.08);
      padding: 0.8rem 1rem; border-radius: $border-radius; margin: 1.2rem 0 1rem;
    }

    .btn-submit {
      width: 100%; padding: 0.8rem; background: $primary-color; color: #fff; border: none;
      border-radius: $border-radius; font-weight: bold; font-size: 1.1rem; cursor: pointer;
      &:hover:not(:disabled) { background: $primary-dark; }
      &:disabled { opacity: 0.5; cursor: not-allowed; }
    }
  }
}
</style>
