// src/store/cart.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const useCartStore = defineStore('cart', () => {
  // 從 localStorage 恢復購物車資料
  const savedCart = JSON.parse(localStorage.getItem('gfmotor_cart') || '[]');
  const items = ref(savedCart);

  // 持久化到 localStorage
  const persist = () => {
    localStorage.setItem('gfmotor_cart', JSON.stringify(items.value));
  };

  const totalItems = computed(() => items.value.reduce((sum, i) => sum + i.quantity, 0));
  const totalAmount = computed(() => items.value.reduce((sum, i) => sum + i.quantity * i.price, 0));

  function addItem(product) {
    const existing = items.value.find(i => i.product_id === product.id);
    if (existing) {
      if (existing.quantity < product.stock) {
        existing.quantity++;
      }
    } else {
      items.value.push({
        product_id: product.id,
        name: product.name,
        price: product.price,
        image_url: product.image_url,
        stock: product.stock,
        quantity: 1
      });
    }
    persist();
  }

  function removeItem(productId) {
    items.value = items.value.filter(i => i.product_id !== productId);
    persist();
  }

  function updateQuantity(productId, qty) {
    const item = items.value.find(i => i.product_id === productId);
    if (item) {
      item.quantity = Math.max(1, Math.min(qty, item.stock));
      persist();
    }
  }

  function clearCart() {
    items.value = [];
    persist();
  }

  return { items, totalItems, totalAmount, addItem, removeItem, updateQuantity, clearCart };
});
