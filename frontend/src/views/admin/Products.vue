<template>
  <div class="admin-shop">
    <div class="section-header">
      <div>
        <h2>商城管理</h2>
        <p>管理網站商品、分類、線上訂單與商城金流 / 物流設定。</p>
      </div>
    </div>

    <div class="tabs">
      <button v-for="tab in tabs" :key="tab.key" type="button" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">
        {{ tab.label }}
      </button>
    </div>

    <section v-if="activeTab === 'products'" class="panel">
      <div class="panel-toolbar">
        <div class="filters">
          <input v-model.trim="productSearch" type="text" placeholder="搜尋商品名稱" />
          <select v-model="productStatusFilter">
            <option value="">全部狀態</option>
            <option value="active">上架中</option>
            <option value="inactive">已下架</option>
          </select>
          <select v-model="productCategoryFilter">
            <option value="">全部分類</option>
            <option value="uncategorized">未分類</option>
            <option v-for="category in categories" :key="category.id" :value="String(category.id)">
              {{ category.name }}
            </option>
          </select>
        </div>
        <button class="btn btn-primary" type="button" @click="openProductModal()">新增商品</button>
      </div>

      <div v-if="loadingProducts" class="loading">載入商品中...</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>商品</th>
              <th>分類</th>
              <th>價格</th>
              <th>庫存</th>
              <th>狀態</th>
              <th>建立時間</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="product in filteredProducts" :key="product.id">
              <td>
                <div class="product-cell">
                  <img v-if="product.image_url" :src="product.image_url" :alt="product.name" />
                  <div v-else class="image-placeholder">無圖</div>
                  <div>
                    <strong>{{ product.name }}</strong>
                    <span>{{ product.description || '無描述' }}</span>
                  </div>
                </div>
              </td>
              <td>{{ productCategoryName(product) }}</td>
              <td class="amount">NT$ {{ formatNumber(product.price) }}</td>
              <td>{{ formatNumber(product.stock) }}</td>
              <td><span class="status-tag" :class="product.is_active ? 'active' : 'inactive'">{{ product.is_active ? '上架中' : '已下架' }}</span></td>
              <td>{{ formatDate(product.created_at) }}</td>
              <td class="action-cell">
                <button class="btn btn-sm" type="button" @click="toggleProduct(product)">{{ product.is_active ? '下架' : '上架' }}</button>
                <button class="btn btn-sm" type="button" @click="openProductModal(product)">編輯</button>
                <button class="btn btn-sm btn-danger" type="button" @click="removeProduct(product)">刪除</button>
              </td>
            </tr>
            <tr v-if="filteredProducts.length === 0">
              <td colspan="7" class="empty-row">查無符合條件的商品。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="activeTab === 'categories'" class="panel">
      <div class="panel-toolbar">
        <div>
          <h3>商品分類</h3>
          <p>分類會用在商品管理與前台商品瀏覽。</p>
        </div>
      </div>

      <form class="inline-form" @submit.prevent="submitCategory">
        <input v-model.trim="categoryForm.name" type="text" placeholder="分類名稱" required />
        <input v-model.number="categoryForm.sort_order" type="number" placeholder="排序" />
        <button class="btn btn-primary" type="submit" :disabled="savingCategory">{{ savingCategory ? '儲存中...' : '新增分類' }}</button>
      </form>

      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>分類名稱</th>
              <th>排序</th>
              <th>狀態</th>
              <th>建立時間</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="category in categories" :key="category.id">
              <template v-if="editingCategoryId === category.id">
                <td><input v-model.trim="categoryDraft.name" class="inline-input" /></td>
                <td><input v-model.number="categoryDraft.sort_order" class="inline-input" type="number" /></td>
                <td>{{ category.is_active ? '啟用' : '停用' }}</td>
                <td>{{ formatDate(category.created_at) }}</td>
                <td class="action-cell">
                  <button class="btn btn-sm btn-save" type="button" @click="saveCategory(category)">儲存</button>
                  <button class="btn btn-sm btn-outline" type="button" @click="cancelEditCategory">取消</button>
                </td>
              </template>
              <template v-else>
                <td><strong>{{ category.name }}</strong></td>
                <td>{{ category.sort_order }}</td>
                <td><span class="status-tag" :class="category.is_active ? 'active' : 'inactive'">{{ category.is_active ? '啟用' : '停用' }}</span></td>
                <td>{{ formatDate(category.created_at) }}</td>
                <td class="action-cell">
                  <button class="btn btn-sm" type="button" @click="startEditCategory(category)">編輯</button>
                  <button class="btn btn-sm" type="button" @click="toggleCategory(category)">{{ category.is_active ? '停用' : '啟用' }}</button>
                </td>
              </template>
            </tr>
            <tr v-if="categories.length === 0">
              <td colspan="5" class="empty-row">尚未建立商品分類。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="activeTab === 'orders'" class="panel">
      <div class="panel-toolbar">
        <div class="filters">
          <input v-model.trim="orderSearch" type="text" placeholder="搜尋會員、電話、訂單編號" />
          <select v-model="orderStatusFilter">
            <option value="">全部狀態</option>
            <option v-for="(label, key) in orderStatusMap" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>
        <button class="btn btn-outline" type="button" @click="fetchShopOrders">重新整理</button>
      </div>

      <div v-if="loadingOrders" class="loading">載入商城訂單中...</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>訂單編號</th>
              <th>會員</th>
              <th>電話</th>
              <th>金額</th>
              <th>付款狀態</th>
              <th>商品狀態</th>
              <th>建立時間</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in filteredShopOrders" :key="order.id">
              <td>#{{ order.id }}</td>
              <td>{{ order.recipient_name }}</td>
              <td>{{ order.recipient_phone }}</td>
              <td class="amount">NT$ {{ formatNumber(order.total_amount) }}</td>
              <td>
                <select v-model="order.status" class="status-select" @change="changeOrderStatus(order)">
                  <option v-for="(label, key) in orderStatusMap" :key="key" :value="key">{{ label }}</option>
                </select>
              </td>
              <td>{{ summarizeItemStatus(order) }}</td>
              <td>{{ formatDateTime(order.created_at) }}</td>
              <td class="action-cell">
                <button class="btn btn-sm" type="button" @click="openOrderDetail(order)">詳情</button>
                <button v-if="order.status !== 'CANCELED'" class="btn btn-sm btn-danger" type="button" @click="cancelShopOrder(order)">取消</button>
              </td>
            </tr>
            <tr v-if="filteredShopOrders.length === 0">
              <td colspan="8" class="empty-row">目前沒有符合條件的網站訂單。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="activeTab === 'payments'" class="panel settings-panel">
      <div class="panel-toolbar">
        <div>
          <h3>金流設定</h3>
          <p>第一版僅保存付款方式與說明，不串接第三方金流。</p>
        </div>
        <button class="btn btn-primary" type="button" :disabled="savingSettings" @click="saveShopSettings">
          {{ savingSettings ? '儲存中...' : '儲存設定' }}
        </button>
      </div>
      <div class="form-grid">
        <label>可用付款方式
          <textarea v-model="settingsDraft.shop_payment_methods" rows="4" placeholder="例如：ATM 轉帳、店取付款、信用卡（未串接）"></textarea>
        </label>
        <label>付款說明
          <textarea v-model="settingsDraft.shop_payment_note" rows="4" placeholder="顯示給後台或後續前台使用的付款說明"></textarea>
        </label>
        <label>匯款資訊
          <textarea v-model="settingsDraft.shop_payment_bank_info" rows="4" placeholder="銀行、帳號、戶名等"></textarea>
        </label>
      </div>
    </section>

    <section v-if="activeTab === 'shipping'" class="panel settings-panel">
      <div class="panel-toolbar">
        <div>
          <h3>物流設定</h3>
          <p>第一版保存配送方式、基本運費與免運門檻，不串接物流服務。</p>
        </div>
        <button class="btn btn-primary" type="button" :disabled="savingSettings" @click="saveShopSettings">
          {{ savingSettings ? '儲存中...' : '儲存設定' }}
        </button>
      </div>
      <div class="form-grid">
        <label>配送方式
          <textarea v-model="settingsDraft.shop_shipping_methods" rows="4" placeholder="例如：店取、宅配、超商取貨（未串接）"></textarea>
        </label>
        <label>基本運費
          <input v-model="settingsDraft.shop_base_shipping_fee" type="number" min="0" />
        </label>
        <label>免運門檻
          <input v-model="settingsDraft.shop_free_shipping_threshold" type="number" min="0" />
        </label>
        <label>物流說明
          <textarea v-model="settingsDraft.shop_shipping_note" rows="4" placeholder="配送時間、注意事項、取貨提醒等"></textarea>
        </label>
      </div>
    </section>

    <div class="modal-overlay" v-if="showProductModal" @click.self="closeProductModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingProductId ? '編輯商品' : '新增商品' }}</h3>
          <button class="btn btn-outline" type="button" @click="closeProductModal">關閉</button>
        </div>
        <form @submit.prevent="submitProduct">
          <div class="form-row">
            <label>商品名稱<input v-model.trim="productForm.name" type="text" required /></label>
            <label>分類
              <select v-model="productForm.category_id">
                <option value="">未分類</option>
                <option v-for="category in activeCategories" :key="category.id" :value="String(category.id)">
                  {{ category.name }}
                </option>
              </select>
            </label>
          </div>
          <div class="form-row">
            <label>價格<input v-model.number="productForm.price" type="number" min="0" required /></label>
            <label>庫存<input v-model.number="productForm.stock" type="number" min="0" required /></label>
          </div>
          <div class="form-row">
            <label>庫存類型
              <select v-model="productForm.inventory_type">
                <option value="SHOP">商品庫存</option>
                <option value="PART">零件 / 耗材庫存</option>
                <option value="BOTH">兩者皆可</option>
              </select>
            </label>
            <label>低庫存門檻<input v-model.number="productForm.low_stock_threshold" type="number" min="0" required /></label>
          </div>
          <label>商品描述<textarea v-model="productForm.description" rows="3"></textarea></label>
          <label>商品圖片<input type="file" accept="image/*" @change="onProductFileChange" /></label>
          <div v-if="productPreviewUrl" class="preview">
            <img :src="productPreviewUrl" alt="商品預覽" />
          </div>
          <div class="form-actions">
            <button class="btn btn-outline" type="button" @click="closeProductModal">取消</button>
            <button class="btn btn-primary" type="submit" :disabled="savingProduct">{{ savingProduct ? '儲存中...' : '儲存商品' }}</button>
          </div>
        </form>
      </div>
    </div>

    <div class="modal-overlay" v-if="selectedOrder" @click.self="selectedOrder = null">
      <div class="modal modal-wide">
        <div class="modal-header">
          <div>
            <h3>商城訂單 #{{ selectedOrder.id }}</h3>
            <p>{{ selectedOrder.recipient_name }} / {{ selectedOrder.recipient_phone }}</p>
          </div>
          <button class="btn btn-outline" type="button" @click="selectedOrder = null">關閉</button>
        </div>
        <div class="detail-grid">
          <div><span>來源</span><strong>網站訂單</strong></div>
          <div><span>付款狀態</span><strong>{{ orderStatusMap[selectedOrder.status] || selectedOrder.status }}</strong></div>
          <div><span>總金額</span><strong>NT$ {{ formatNumber(selectedOrder.total_amount) }}</strong></div>
          <div><span>收件地址</span><strong>{{ selectedOrder.shipping_address || '店取' }}</strong></div>
          <div><span>建立時間</span><strong>{{ formatDateTime(selectedOrder.created_at) }}</strong></div>
          <div><span>備註</span><strong>{{ selectedOrder.notes || '無' }}</strong></div>
        </div>
        <h4>商品明細</h4>
        <table class="data-table compact">
          <thead>
            <tr>
              <th>商品</th>
              <th>數量</th>
              <th>單價</th>
              <th>小計</th>
              <th>商品狀態</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in selectedOrder.items || []" :key="item.id">
              <td>{{ item.product?.name || `商品 #${item.product_id}` }}</td>
              <td>{{ item.quantity }}</td>
              <td>NT$ {{ formatNumber(item.unit_price) }}</td>
              <td>NT$ {{ formatNumber(item.quantity * item.unit_price) }}</td>
              <td>
                <select v-model="item.status" class="status-select" :disabled="selectedOrder.status === 'COMPLETED'" @change="changeItemStatus(selectedOrder, item)">
                  <option v-for="(label, key) in itemStatusMap" :key="key" :value="key">{{ label }}</option>
                </select>
              </td>
            </tr>
            <tr v-if="!selectedOrder.items?.length">
              <td colspan="5" class="empty-row">此訂單沒有商品明細。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useSiteStore } from '../../store/site';
import {
  cancelOrder,
  createProduct,
  createProductCategory,
  deleteProduct,
  getProductCategories,
  getProducts,
  getShopOrders,
  toggleProductActive,
  toggleProductCategory,
  updateOrderItemStatus,
  updateOrderStatus,
  updateProduct,
  updateProductCategory
} from '../../api/admin';

const siteStore = useSiteStore();
const { settings } = storeToRefs(siteStore);

const tabs = [
  { key: 'products', label: '商品管理' },
  { key: 'categories', label: '商品分類' },
  { key: 'orders', label: '商城訂單' },
  { key: 'payments', label: '金流設定' },
  { key: 'shipping', label: '物流設定' }
];

const activeTab = ref('products');
const products = ref([]);
const categories = ref([]);
const shopOrders = ref([]);
const loadingProducts = ref(false);
const loadingOrders = ref(false);

const productSearch = ref('');
const productStatusFilter = ref('');
const productCategoryFilter = ref('');
const orderSearch = ref('');
const orderStatusFilter = ref('');

const showProductModal = ref(false);
const editingProductId = ref(null);
const savingProduct = ref(false);
const productPreviewUrl = ref('');
const selectedProductFile = ref(null);
const productForm = reactive(defaultProductForm());

const categoryForm = reactive({ name: '', sort_order: 0 });
const savingCategory = ref(false);
const editingCategoryId = ref(null);
const categoryDraft = reactive({ name: '', sort_order: 0 });

const selectedOrder = ref(null);
const savingSettings = ref(false);
const settingsDraft = reactive({
  shop_payment_methods: '',
  shop_payment_note: '',
  shop_payment_bank_info: '',
  shop_shipping_methods: '',
  shop_base_shipping_fee: '0',
  shop_free_shipping_threshold: '0',
  shop_shipping_note: ''
});

const orderStatusMap = {
  PENDING: '未付款',
  DEPOSIT_PAID: '已付訂金',
  FULL_PAID: '已付款',
  COMPLETED: '已完成',
  CANCELED: '已取消'
};

const itemStatusMap = {
  NOT_ORDERED: '尚未訂貨',
  ORDERED: '已訂貨',
  ARRIVED_NEED_NOTIFY: '已到貨需通知',
  NOTIFIED: '已通知',
  COMPLETED: '已結案'
};

const activeCategories = computed(() => categories.value.filter(category => category.is_active));

const filteredProducts = computed(() => {
  const keyword = productSearch.value.toLowerCase();
  return products.value.filter(product => {
    const matchesKeyword = !keyword || product.name?.toLowerCase().includes(keyword);
    const matchesStatus =
      !productStatusFilter.value ||
      (productStatusFilter.value === 'active' && product.is_active) ||
      (productStatusFilter.value === 'inactive' && !product.is_active);
    const matchesCategory =
      !productCategoryFilter.value ||
      (productCategoryFilter.value === 'uncategorized' && !product.category_id) ||
      String(product.category_id || '') === productCategoryFilter.value;
    return matchesKeyword && matchesStatus && matchesCategory;
  });
});

const filteredShopOrders = computed(() => {
  const keyword = orderSearch.value.toLowerCase();
  return shopOrders.value.filter(order => {
    const matchesKeyword =
      !keyword ||
      String(order.id).includes(keyword) ||
      (order.recipient_name || '').toLowerCase().includes(keyword) ||
      (order.recipient_phone || '').includes(keyword);
    const matchesStatus = !orderStatusFilter.value || order.status === orderStatusFilter.value;
    return order.source === 'online' && matchesKeyword && matchesStatus;
  });
});

function defaultProductForm() {
  return {
    name: '',
    category_id: '',
    price: 0,
    stock: 0,
    inventory_type: 'BOTH',
    low_stock_threshold: 5,
    description: ''
  };
}

const formatNumber = (value) => Number(value || 0).toLocaleString();

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

const productCategoryName = (product) => product.category_info?.name || product.category || '未分類';

const selectedCategoryName = (categoryId) => {
  const category = categories.value.find(item => String(item.id) === String(categoryId));
  return category?.name || '';
};

const summarizeItemStatus = (order) => {
  const items = order.items || [];
  if (!items.length) return '無商品明細';
  const counts = items.reduce((acc, item) => {
    acc[item.status] = (acc[item.status] || 0) + 1;
    return acc;
  }, {});
  return Object.entries(counts)
    .map(([status, count]) => `${itemStatusMap[status] || status} ${count}`)
    .join('、');
};

const fetchProducts = async () => {
  loadingProducts.value = true;
  try {
    products.value = await getProducts();
  } catch (error) {
    alert(`載入商品失敗：${getErrorMessage(error)}`);
  } finally {
    loadingProducts.value = false;
  }
};

const fetchCategories = async () => {
  categories.value = await getProductCategories();
};

const fetchShopOrders = async () => {
  loadingOrders.value = true;
  try {
    shopOrders.value = (await getShopOrders()).filter(order => order.source === 'online');
  } catch (error) {
    alert(`載入商城訂單失敗：${getErrorMessage(error)}`);
  } finally {
    loadingOrders.value = false;
  }
};

const loadSettings = async () => {
  await siteStore.fetchSettings();
  Object.assign(settingsDraft, {
    shop_payment_methods: settings.value.shop_payment_methods || '',
    shop_payment_note: settings.value.shop_payment_note || '',
    shop_payment_bank_info: settings.value.shop_payment_bank_info || '',
    shop_shipping_methods: settings.value.shop_shipping_methods || '',
    shop_base_shipping_fee: settings.value.shop_base_shipping_fee || '0',
    shop_free_shipping_threshold: settings.value.shop_free_shipping_threshold || '0',
    shop_shipping_note: settings.value.shop_shipping_note || ''
  });
};

const openProductModal = (product = null) => {
  editingProductId.value = product?.id || null;
  Object.assign(productForm, defaultProductForm(), product ? {
    name: product.name || '',
    category_id: product.category_id ? String(product.category_id) : '',
    price: product.price || 0,
    stock: product.stock || 0,
    inventory_type: product.inventory_type || 'BOTH',
    low_stock_threshold: product.low_stock_threshold ?? 5,
    description: product.description || ''
  } : {});
  productPreviewUrl.value = product?.image_url || '';
  selectedProductFile.value = null;
  showProductModal.value = true;
};

const closeProductModal = () => {
  showProductModal.value = false;
  editingProductId.value = null;
  selectedProductFile.value = null;
  productPreviewUrl.value = '';
};

const onProductFileChange = (event) => {
  const file = event.target.files?.[0];
  selectedProductFile.value = file || null;
  if (file) productPreviewUrl.value = URL.createObjectURL(file);
};

const buildProductFormData = () => {
  const formData = new FormData();
  formData.append('name', productForm.name);
  formData.append('price', Number(productForm.price) || 0);
  formData.append('stock', Number(productForm.stock) || 0);
  formData.append('inventory_type', productForm.inventory_type || 'BOTH');
  formData.append('low_stock_threshold', Number(productForm.low_stock_threshold) || 0);
  formData.append('description', productForm.description || '');
  if (productForm.category_id) {
    formData.append('category_id', Number(productForm.category_id));
    formData.append('category', selectedCategoryName(productForm.category_id));
  } else {
    formData.append('category', '');
  }
  if (selectedProductFile.value) formData.append('file', selectedProductFile.value);
  return formData;
};

const submitProduct = async () => {
  savingProduct.value = true;
  try {
    const formData = buildProductFormData();
    if (editingProductId.value) await updateProduct(editingProductId.value, formData);
    else await createProduct(formData);
    closeProductModal();
    await fetchProducts();
  } catch (error) {
    alert(`儲存商品失敗：${getErrorMessage(error)}`);
  } finally {
    savingProduct.value = false;
  }
};

const toggleProduct = async (product) => {
  try {
    const updated = await toggleProductActive(product.id);
    Object.assign(product, updated);
  } catch (error) {
    alert(`切換商品狀態失敗：${getErrorMessage(error)}`);
  }
};

const removeProduct = async (product) => {
  if (!confirm(`確定要刪除商品「${product.name}」嗎？`)) return;
  try {
    await deleteProduct(product.id);
    await fetchProducts();
  } catch (error) {
    alert(`刪除商品失敗：${getErrorMessage(error)}`);
  }
};

const submitCategory = async () => {
  savingCategory.value = true;
  try {
    await createProductCategory({
      name: categoryForm.name,
      sort_order: Number(categoryForm.sort_order) || 0,
      is_active: 1
    });
    categoryForm.name = '';
    categoryForm.sort_order = 0;
    await fetchCategories();
  } catch (error) {
    alert(`新增分類失敗：${getErrorMessage(error)}`);
  } finally {
    savingCategory.value = false;
  }
};

const startEditCategory = (category) => {
  editingCategoryId.value = category.id;
  categoryDraft.name = category.name;
  categoryDraft.sort_order = category.sort_order || 0;
};

const cancelEditCategory = () => {
  editingCategoryId.value = null;
  categoryDraft.name = '';
  categoryDraft.sort_order = 0;
};

const saveCategory = async (category) => {
  try {
    await updateProductCategory(category.id, {
      name: categoryDraft.name,
      sort_order: Number(categoryDraft.sort_order) || 0
    });
    cancelEditCategory();
    await fetchCategories();
    await fetchProducts();
  } catch (error) {
    alert(`更新分類失敗：${getErrorMessage(error)}`);
  }
};

const toggleCategory = async (category) => {
  try {
    const updated = await toggleProductCategory(category.id);
    Object.assign(category, updated);
  } catch (error) {
    alert(`切換分類狀態失敗：${getErrorMessage(error)}`);
  }
};

const openOrderDetail = (order) => {
  selectedOrder.value = order;
};

const changeOrderStatus = async (order) => {
  try {
    const updated = await updateOrderStatus(order.id, order.status);
    Object.assign(order, updated);
    if (selectedOrder.value?.id === order.id) selectedOrder.value = order;
  } catch (error) {
    alert(`更新訂單狀態失敗：${getErrorMessage(error)}`);
    await fetchShopOrders();
  }
};

const changeItemStatus = async (order, item) => {
  try {
    const updated = await updateOrderItemStatus(item.id, item.status);
    Object.assign(item, updated);
  } catch (error) {
    alert(`更新商品狀態失敗：${getErrorMessage(error)}`);
    await fetchShopOrders();
  }
};

const cancelShopOrder = async (order) => {
  if (!confirm(`確定要取消商城訂單 #${order.id} 嗎？取消後會回補商品庫存。`)) return;
  try {
    const updated = await cancelOrder(order.id);
    Object.assign(order, updated);
    await fetchProducts();
  } catch (error) {
    alert(`取消訂單失敗：${getErrorMessage(error)}`);
  }
};

const saveShopSettings = async () => {
  savingSettings.value = true;
  try {
    const ok = await siteStore.updateSettings({ ...settingsDraft });
    if (ok) alert('商城設定已儲存');
  } catch (error) {
    alert(`儲存設定失敗：${getErrorMessage(error)}`);
  } finally {
    savingSettings.value = false;
  }
};

onMounted(async () => {
  await Promise.all([fetchCategories(), fetchProducts(), fetchShopOrders(), loadSettings()]);
});
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-shop {
  color: $text-primary;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1.25rem;

    h2 {
      color: $primary-light;
      margin: 0 0 0.35rem;
    }

    p {
      color: $text-secondary;
      margin: 0;
      font-size: 0.92rem;
    }
  }

  .tabs {
    display: flex;
    gap: 0.45rem;
    overflow-x: auto;
    border-bottom: 1px solid $medium-grey;
    margin-bottom: 1.25rem;

    button {
      min-height: 42px;
      padding: 0 0.9rem;
      background: transparent;
      border: 0;
      border-bottom: 2px solid transparent;
      color: $text-secondary;
      cursor: pointer;
      white-space: nowrap;

      &.active {
        color: $primary-light;
        border-color: $primary-light;
      }
    }
  }

  .panel {
    min-height: 420px;
  }

  .panel-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;

    h3 {
      color: $text-primary;
      margin: 0 0 0.25rem;
    }

    p {
      color: $text-disabled;
      margin: 0;
      font-size: 0.88rem;
    }
  }

  .filters {
    display: flex;
    gap: 0.7rem;
    flex-wrap: wrap;
  }

  input,
  select,
  textarea {
    min-height: 38px;
    padding: 0.52rem 0.72rem;
    background: $background-color;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    color: $text-primary;
    font-size: 0.9rem;
    box-sizing: border-box;

    &:focus {
      outline: none;
      border-color: $primary-color;
    }
  }

  textarea {
    resize: vertical;
  }

  .table-wrap {
    overflow-x: auto;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    background: $dark-grey;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      padding: 0.78rem 0.85rem;
      border-bottom: 1px solid $medium-grey;
      text-align: left;
      vertical-align: middle;
      white-space: nowrap;
      font-size: 0.88rem;
    }

    th {
      background: $background-color;
      color: $text-secondary;
      font-size: 0.8rem;
      font-weight: 700;
    }

    tbody tr:hover {
      background: rgba($primary-color, 0.05);
    }

    &.compact {
      margin-top: 0.75rem;
    }
  }

  .product-cell {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    min-width: 260px;

    img,
    .image-placeholder {
      width: 52px;
      height: 52px;
      border-radius: $border-radius;
      object-fit: cover;
      flex: 0 0 auto;
    }

    .image-placeholder {
      background: $medium-grey;
      color: $text-disabled;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.78rem;
    }

    strong,
    span {
      display: block;
    }

    span {
      color: $text-disabled;
      margin-top: 0.2rem;
      max-width: 340px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .amount {
    color: $primary-light;
    font-weight: 700;
  }

  .status-tag {
    display: inline-flex;
    min-height: 24px;
    align-items: center;
    padding: 0 0.55rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;

    &.active {
      color: #81c784;
      background: rgba(#81c784, 0.14);
    }

    &.inactive {
      color: #ffb74d;
      background: rgba(#ffb74d, 0.14);
    }
  }

  .status-select {
    min-width: 118px;
  }

  .action-cell {
    display: flex;
    gap: 0.45rem;
  }

  .btn {
    min-height: 34px;
    padding: 0.42rem 0.78rem;
    border: 1px solid $primary-color;
    background: transparent;
    color: $primary-color;
    border-radius: $border-radius;
    cursor: pointer;
    font-size: 0.84rem;

    &:hover {
      background: $primary-color;
      color: #fff;
    }

    &:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }

    &.btn-primary {
      background: $primary-color;
      color: #fff;

      &:hover {
        background: $primary-dark;
      }
    }

    &.btn-outline {
      border-color: $medium-grey;
      color: $text-secondary;

      &:hover {
        background: $medium-grey;
        color: #fff;
      }
    }

    &.btn-danger {
      color: #ff6b6b;
      border-color: #ff6b6b;

      &:hover {
        background: #ff6b6b;
        color: #fff;
      }
    }

    &.btn-sm {
      min-height: 30px;
      padding: 0.3rem 0.62rem;
      font-size: 0.78rem;
    }

    &.btn-save {
      background: $primary-color;
      color: #fff;
    }
  }

  .inline-form {
    display: flex;
    gap: 0.7rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;

    input[type='text'] {
      min-width: 240px;
    }

    input[type='number'] {
      width: 120px;
    }
  }

  .inline-input {
    width: 100%;
    min-width: 120px;
  }

  .settings-panel {
    .form-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1rem;
    }
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.42rem;
    color: $text-secondary;
    font-size: 0.86rem;
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
    width: 620px;
    max-width: 100%;
    max-height: calc(100vh - 2rem);
    overflow: auto;
    background: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    padding: 1.4rem;

    &.modal-wide {
      width: 900px;
    }

    h3,
    h4 {
      color: $primary-light;
      margin: 0;
    }

    h4 {
      margin-top: 1.2rem;
    }

    form {
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
    }
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
    margin-bottom: 1rem;

    p {
      color: $text-secondary;
      margin: 0.25rem 0 0;
    }
  }

  .form-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.8rem;
  }

  .preview {
    img {
      width: 100%;
      max-height: 240px;
      object-fit: cover;
      border-radius: $border-radius;
      border: 1px solid $medium-grey;
    }
  }

  .form-actions {
    display: flex;
    gap: 0.7rem;
    justify-content: flex-end;
  }

  .detail-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;

    div {
      border: 1px solid $medium-grey;
      border-radius: $border-radius;
      padding: 0.75rem;
      background: rgba($background-color, 0.55);
    }

    span,
    strong {
      display: block;
    }

    span {
      color: $text-disabled;
      font-size: 0.78rem;
      margin-bottom: 0.3rem;
    }

    strong {
      color: $text-primary;
      overflow-wrap: anywhere;
    }
  }

  .loading,
  .empty-row {
    color: $text-disabled;
    text-align: center;
    padding: 2rem;
  }

  @media (max-width: 768px) {
    .section-header,
    .panel-toolbar,
    .filters,
    .inline-form {
      flex-direction: column;
      align-items: stretch;
    }

    .filters input,
    .filters select,
    .btn,
    .inline-form input {
      width: 100%;
    }

    .settings-panel .form-grid,
    .form-row,
    .detail-grid {
      grid-template-columns: 1fr;
    }
  }
}
</style>
