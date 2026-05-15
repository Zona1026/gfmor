<template>
  <div class="cart-page">
    <h2>購物車</h2>

    <div v-if="cartItems.length === 0" class="empty-state">
      <div class="empty-icon">🛒</div>
      <p>您的購物車目前是空的</p>
      <router-link to="/products" class="btn-shop">前往商城選購</router-link>
    </div>

    <div v-else>
      <div class="cart-list">
        <div v-for="item in cartItems" :key="item.product_id" class="cart-item">
          <img v-if="item.image_url" :src="item.image_url" :alt="item.name" class="item-image" />
          <div v-else class="item-image placeholder-img"><span>無圖</span></div>
          <div class="item-info">
            <h3>{{ item.name }}</h3>
            <span class="item-price">NT$ {{ item.price?.toLocaleString() }}</span>
          </div>
          <div class="qty-control">
            <button @click="cartStore.updateQuantity(item.product_id, item.quantity - 1)" :disabled="item.quantity <= 1">−</button>
            <span>{{ item.quantity }}</span>
            <button @click="cartStore.updateQuantity(item.product_id, item.quantity + 1)" :disabled="item.quantity >= item.stock">＋</button>
          </div>
          <span class="item-subtotal">NT$ {{ (item.price * item.quantity).toLocaleString() }}</span>
          <button class="btn-remove" @click="cartStore.removeItem(item.product_id)">✕</button>
        </div>
      </div>

      <div class="cart-summary">
        <div class="summary-row">
          <span>共 {{ cartStore.totalItems }} 件商品</span>
          <span class="total">合計 NT$ {{ cartStore.totalAmount.toLocaleString() }}</span>
        </div>
        <div class="summary-actions">
          <button class="btn-outline" @click="cartStore.clearCart()">清空購物車</button>
          <router-link to="/checkout" class="btn-checkout">前往結帳</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia';
import { useCartStore } from '../store/cart';

const cartStore = useCartStore();
const { items: cartItems } = storeToRefs(cartStore);
</script>

<style lang="scss" scoped>
@import '../assets/_variables.scss';

.cart-page {
  padding: 2rem;
  max-width: 900px;
  margin: 1rem auto;

  h2 { color: $primary-light; text-align: center; margin-bottom: 2rem; font-size: 2.2rem; text-shadow: 0 2px 10px rgba(0,0,0,0.5); }

  .empty-state {
    text-align: center; padding: 4rem 2rem; color: $text-disabled;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: linear-gradient(145deg, #2a2a2a, #1f1f1f);
    border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.2);

    .empty-icon { font-size: 4rem; margin-bottom: 1rem; opacity: 0.5; filter: grayscale(100%); }
    p { font-size: 1.2rem; margin-bottom: 2rem; }
    .btn-shop {
      display: inline-block; padding: 0.8rem 2.5rem; background: $primary-color; color: #fff;
      border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 1.1rem;
      transition: $transition-base; box-shadow: 0 4px 15px rgba($primary-color, 0.4);
      &:hover { background: $primary-light; transform: translateY(-2px); box-shadow: 0 6px 20px rgba($primary-color, 0.6); }
    }
  }

  .cart-list { display: flex; flex-direction: column; gap: 1.5rem; }

  .cart-item {
    display: flex; align-items: center; gap: 1.5rem; padding: 1.5rem;
    background: linear-gradient(145deg, #2a2a2a, #1f1f1f); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px;
    transition: $transition-base; box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    &:hover { box-shadow: 0 8px 25px rgba(0,0,0,0.3); border-color: rgba(255,255,255,0.1); transform: translateX(5px); }

    .item-image { width: 100px; height: 100px; object-fit: cover; border-radius: 8px; flex-shrink: 0; }
    .placeholder-img {
      width: 100px; height: 100px; background: $medium-grey; border-radius: 8px;
      display: flex; align-items: center; justify-content: center; color: $text-disabled; font-size: 0.85rem;
    }

    .item-info {
      flex: 1;
      h3 { margin: 0 0 0.5rem; color: $text-primary; font-size: 1.1rem; }
      .item-price { color: $text-disabled; font-size: 0.95rem; }
    }

    .qty-control {
      display: flex; align-items: center; gap: 0.5rem; background: rgba(0,0,0,0.2); padding: 0.3rem; border-radius: 20px;
      button {
        width: 32px; height: 32px; border: none; background: rgba(255,255,255,0.1);
        color: $text-primary; border-radius: 50%; cursor: pointer; font-size: 1.2rem;
        display: flex; align-items: center; justify-content: center; transition: $transition-base;
        &:hover:not(:disabled) { background: $primary-color; }
        &:disabled { opacity: 0.3; cursor: not-allowed; }
      }
      span { min-width: 2rem; text-align: center; color: $text-primary; font-weight: bold; }
    }

    .item-subtotal { color: $primary-light; font-weight: 800; min-width: 120px; text-align: right; font-size: 1.2rem; }

    .btn-remove {
      border: none; background: rgba(255, 107, 107, 0.1); color: #ff6b6b; cursor: pointer;
      width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
      transition: $transition-base; font-size: 1.2rem;
      &:hover { background: #ff6b6b; color: #fff; transform: rotate(90deg); }
    }

    @media (max-width: 768px) {
      flex-wrap: wrap; position: relative;
      .btn-remove { position: absolute; top: 1rem; right: 1rem; }
      .item-subtotal { width: 100%; text-align: right; margin-top: 1rem; }
    }
  }

  .cart-summary {
    margin-top: 2.5rem; padding: 2rem; background: linear-gradient(145deg, #2a2a2a, #1f1f1f);
    border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.2);

    .summary-row {
      display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 2rem;
      color: $text-secondary; padding-bottom: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.1);
      .total { color: $primary-light; font-size: 1.8rem; font-weight: 800; text-shadow: 0 0 10px rgba(255,255,255,0.1); }
    }

    .summary-actions {
      display: flex; gap: 1.5rem; justify-content: flex-end;

      .btn-outline {
        padding: 0.8rem 2rem; background: transparent; border: 1px solid $light-grey;
        color: $text-secondary; border-radius: 30px; cursor: pointer; transition: $transition-base; font-weight: bold;
        &:hover { background: rgba(255,255,255,0.1); color: #fff; }
      }

      .btn-checkout {
        padding: 0.8rem 2.5rem; background: $primary-color; color: #fff; border: none;
        border-radius: 30px; text-decoration: none; font-weight: bold; font-size: 1.1rem;
        transition: $transition-base; box-shadow: 0 4px 15px rgba($primary-color, 0.4);
        &:hover { background: $primary-light; transform: translateY(-2px); box-shadow: 0 6px 20px rgba($primary-color, 0.6); }
      }
      
      @media (max-width: 600px) {
        flex-direction: column;
        .btn-outline, .btn-checkout { width: 100%; text-align: center; }
      }
    }
  }
}
</style>
