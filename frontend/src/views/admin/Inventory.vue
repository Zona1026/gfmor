<template>
  <div class="admin-inventory">
    <div class="section-header">
      <div>
        <h2>庫存管理</h2>
      </div>
      <span class="role-chip">{{ adminUser?.role || '一般' }}</span>
    </div>

    <div class="tabs">
      <button
        v-for="tab in visibleTabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="selectTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <section v-if="activeTab === 'shop'" class="inventory-panel">
      <div class="panel-title list-heading">
        <h3>商品列表</h3>
        <button v-if="canManageInventory" class="btn btn-primary" type="button" @click="openCreateModal('SHOP')">
          ＋ 新增商品
        </button>
      </div>
      <InventoryTable :items="shopItems" />
    </section>

    <section v-if="activeTab === 'parts'" class="inventory-panel">
      <div class="panel-title list-heading">
        <h3>零件列表</h3>
        <button v-if="canManageInventory" class="btn btn-primary" type="button" @click="openCreateModal('PART')">
          ＋ 新增零件
        </button>
      </div>
      <InventoryTable :items="partItems" />
    </section>

    <section v-if="activeTab === 'movements'" class="panel">
      <div class="panel-title">
        <h3>庫存異動紀錄</h3>
        <button class="btn btn-outline" type="button" @click="fetchMovements">重新整理</button>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>時間</th>
              <th>品項</th>
              <th>類型</th>
              <th>異動</th>
              <th>異動前</th>
              <th>異動後</th>
              <th>來源</th>
              <th>原因</th>
              <th v-if="canUseCriticalInventory">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="movement in movements" :key="movement.id">
              <td>{{ formatDate(movement.created_at) }}</td>
              <td>{{ movement.product_name || `#${movement.product_id}` }}</td>
              <td>{{ movementTypeLabel(movement.movement_type) }}</td>
              <td :class="{ positive: movement.quantity_delta > 0, negative: movement.quantity_delta < 0 }">
                {{ signedNumber(movement.quantity_delta) }}
              </td>
              <td>{{ formatNumber(movement.stock_before) }}</td>
              <td>{{ formatNumber(movement.stock_after) }}</td>
              <td>{{ sourceLabel(movement.source_type, movement.source_id) }}</td>
              <td>{{ movement.reason || '-' }}</td>
            </tr>
            <tr v-if="movements.length === 0">
              <td colspan="8" class="empty-row">尚無庫存異動。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="activeTab === 'reservations'" class="panel">
      <div class="panel-title">
        <h3>庫存預留紀錄</h3>
        <select v-model="reservationStatus" @change="fetchReservations">
          <option value="">全部狀態</option>
          <option value="ACTIVE">預留中</option>
          <option value="CONSUMED">已扣庫存</option>
          <option value="RELEASED">已釋放</option>
        </select>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>建立時間</th>
              <th>品項</th>
              <th>數量</th>
              <th>狀態</th>
              <th>來源</th>
              <th>原因</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="reservation in reservations" :key="reservation.id">
              <td>{{ formatDate(reservation.created_at) }}</td>
              <td>{{ reservation.product_name || `#${reservation.product_id}` }}</td>
              <td>{{ formatNumber(reservation.quantity) }}</td>
              <td><span class="status-tag" :class="reservation.status.toLowerCase()">{{ reservationStatusLabel(reservation.status) }}</span></td>
              <td>{{ sourceLabel(reservation.source_type, reservation.source_id) }}</td>
              <td>{{ reservation.reason || '-' }}</td>
              <td v-if="canUseCriticalInventory">
                <button
                  v-if="canReleaseReservation(reservation)"
                  class="btn btn-sm btn-danger"
                  type="button"
                  @click="releaseReservation(reservation)"
                >
                  取消預留
                </button>
                <span v-else>-</span>
              </td>
            </tr>
            <tr v-if="reservations.length === 0">
              <td :colspan="canUseCriticalInventory ? 7 : 6" class="empty-row">尚無預留紀錄。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="activeTab === 'stocktake'" class="panel">
      <div class="panel-title">
        <div>
          <h3>盤點表</h3>
          <p class="panel-description">輸入實際盤點數量，系統會顯示差異並留下庫存異動紀錄。</p>
        </div>
        <button class="btn btn-outline" type="button" @click="fetchItems">重新整理</button>
      </div>
      <div class="table-wrap stocktake-wrap">
        <table class="data-table stocktake-table">
          <thead>
            <tr>
              <th>品項</th>
              <th>類型</th>
              <th>帳面庫存</th>
              <th>預留</th>
              <th>可用</th>
              <th>實際盤點</th>
              <th>差異</th>
              <th v-if="canUseCriticalInventory">原因</th>
              <th v-if="canUseCriticalInventory">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in allItems" :key="item.id">
              <td>
                <strong class="product-name">{{ item.name }}</strong>
                <small>{{ productCategory(item) }}</small>
              </td>
              <td>{{ inventoryTypeLabel(item.inventory_type) }}</td>
              <td>{{ stockValue(item.stock) }}</td>
              <td>{{ stockValue(item.reserved_stock) }}</td>
              <td>{{ stockValue(item.available_stock) }}</td>
              <td>
                <input
                  v-if="canUseCriticalInventory"
                  v-model.number="stocktakeDrafts[item.id].stock_after"
                  class="count-input"
                  type="number"
                  min="0"
                />
                <span v-else>{{ stockValue(item.stock) }}</span>
              </td>
              <td :class="stocktakeDifference(item) > 0 ? 'positive' : stocktakeDifference(item) < 0 ? 'negative' : ''">
                {{ signedNumber(stocktakeDifference(item)) }}
              </td>
              <td v-if="canUseCriticalInventory">
                <input v-model.trim="stocktakeDrafts[item.id].reason" class="reason-input" type="text" placeholder="盤點原因" />
              </td>
              <td v-if="canUseCriticalInventory">
                <button
                  class="btn btn-sm btn-primary"
                  type="button"
                  :disabled="savingAdjustmentId === item.id || stocktakeDifference(item) === 0"
                  @click="submitStocktake(item)"
                >
                  {{ savingAdjustmentId === item.id ? '儲存中' : '盤點入帳' }}
                </button>
              </td>
            </tr>
            <tr v-if="allItems.length === 0">
              <td :colspan="canUseCriticalInventory ? 9 : 7" class="empty-row">尚無可盤點品項。</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!canUseCriticalInventory" class="permission-note">僅最高級管理員可將盤點差異入帳。</p>

      <div v-if="canUseCriticalInventory" class="panel-title sub-title">
        <h3>報廢出庫</h3>
      </div>
      <form v-if="canUseCriticalInventory" class="adjust-form" @submit.prevent="submitScrap">
        <label>
          品項
          <select v-model.number="scrapForm.product_id" required>
            <option value="">請選擇品項</option>
            <option v-for="item in allItems" :key="item.id" :value="item.id">
              {{ item.name }} / 可用 {{ formatNumber(item.available_stock) }}
            </option>
          </select>
        </label>
        <label>
          報廢數量
          <input v-model.number="scrapForm.quantity" type="number" min="1" required />
        </label>
        <label class="reason-field">
          原因
          <textarea v-model.trim="scrapForm.reason" rows="3" required></textarea>
        </label>
        <button class="btn btn-danger" type="submit" :disabled="savingScrap">
          {{ savingScrap ? '處理中...' : '報廢出庫' }}
        </button>
      </form>
    </section>

    <section v-if="activeTab === 'low'" class="inventory-panel">
      <div class="panel-title list-heading"><h3>低庫存提醒</h3></div>
      <InventoryTable :items="lowStockItems" />
    </section>

    <div v-if="showCreateModal && canManageInventory" class="modal-overlay" @click.self="closeCreateModal">
      <div class="modal" role="dialog" aria-modal="true" :aria-label="createModalTitle">
        <div class="modal-header">
          <h3>{{ createModalTitle }}</h3>
          <button class="btn btn-outline" type="button" @click="closeCreateModal">關閉</button>
        </div>
        <form class="create-form" @submit.prevent="submitCreateItem">
          <div class="form-grid">
            <label>
              品項名稱
              <input v-model.trim="createForm.name" type="text" required />
            </label>
            <label>
              分類
              <select v-model="createForm.category_id">
                <option value="">未分類</option>
                <option v-for="category in activeCategories" :key="category.id" :value="String(category.id)">
                  {{ category.name }}
                </option>
              </select>
            </label>
            <label>
              售價
              <input v-model.number="createForm.price" type="number" min="0" required />
            </label>
            <label>
              初始庫存
              <input v-model.number="createForm.stock" type="number" min="0" required />
            </label>
            <label>
              庫存用途
              <select v-model="createForm.inventory_type" required>
                <option value="SHOP">商城商品</option>
                <option value="PART">工單零件 / 耗材</option>
                <option value="BOTH">商城與工單共用</option>
              </select>
            </label>
            <label>
              低庫存門檻
              <input v-model.number="createForm.low_stock_threshold" type="number" min="0" required />
            </label>
          </div>
          <label>
            描述
            <textarea v-model.trim="createForm.description" rows="3"></textarea>
          </label>
          <label>
            圖片
            <input type="file" accept="image/*" @change="onCreateFileChange" />
          </label>
          <div class="form-actions">
            <button class="btn btn-outline" type="button" @click="closeCreateModal">取消</button>
            <button class="btn btn-primary" type="submit" :disabled="savingCreate">
              {{ savingCreate ? '新增中...' : '確認新增' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, reactive, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../../store/auth';
import {
  adjustInventory,
  createProduct,
  getInventoryItems,
  getInventoryMovements,
  getInventoryReservations,
  getProductCategories,
  releaseInventoryReservation,
  scrapInventory
} from '../../api/admin';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const { adminUser } = storeToRefs(authStore);

const managerRoles = ['最高級', '管理層'];
const canManageInventory = computed(() => managerRoles.includes(adminUser.value?.role));
const canUseCriticalInventory = computed(() => adminUser.value?.role === '最高級');

const routeTabMap = { products: 'shop', parts: 'parts', stocktake: 'stocktake' };
const tabRouteMap = {
  shop: 'AdminInventoryProducts',
  parts: 'AdminInventoryParts',
  stocktake: 'AdminInventoryStocktake'
};
const activeTab = ref(routeTabMap[route.meta.inventorySection] || 'shop');
const loading = ref(false);
const savingAdjustmentId = ref(null);
const savingScrap = ref(false);
const savingCreate = ref(false);
const showCreateModal = ref(false);
const createItemType = ref('SHOP');
const selectedCreateFile = ref(null);
const shopItems = ref([]);
const partItems = ref([]);
const allItems = ref([]);
const lowStockItems = ref([]);
const movements = ref([]);
const reservations = ref([]);
const categories = ref([]);
const reservationStatus = ref('');
const stocktakeDrafts = reactive({});

const defaultCreateForm = (inventoryType = 'SHOP') => ({
  name: '',
  category_id: '',
  price: 0,
  stock: 0,
  inventory_type: inventoryType,
  low_stock_threshold: 5,
  description: ''
});
const createForm = reactive(defaultCreateForm());

const scrapForm = reactive({
  product_id: '',
  quantity: 1,
  reason: ''
});

const tabs = [
  { key: 'shop', label: '商品列表' },
  { key: 'parts', label: '零件列表' },
  { key: 'stocktake', label: '盤點表' },
  { key: 'movements', label: '庫存異動紀錄' },
  { key: 'reservations', label: '庫存預留紀錄' },
  { key: 'low', label: '低庫存提醒' }
];

const visibleTabs = computed(() => tabs.filter(tab => {
  if (tab.superOnly) return canUseCriticalInventory.value;
  if (tab.managerOnly) return canManageInventory.value;
  return true;
}));

function formatNumber(value) {
  return Number(value || 0).toLocaleString();
}

function stockValue(value) {
  return value === null || value === undefined ? '-' : formatNumber(value);
}

function signedNumber(value) {
  const number = Number(value || 0);
  return `${number > 0 ? '+' : ''}${formatNumber(number)}`;
}

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-TW', { hour12: false });
}

function inventoryTypeLabel(type) {
  const map = { SHOP: '商品', PART: '零件 / 耗材', BOTH: '皆可' };
  return map[type] || type || '-';
}

function movementTypeLabel(type) {
  const map = {
    MANUAL_ADJUST: '手動調整',
    SHOP_ORDER_CONSUME: '商城出庫',
    WORK_ORDER_CONSUME: '工單出庫',
    INSTORE_SALE: '現場銷售',
    CANCEL_RESTORE: '取消回補',
    PURCHASE_RECEIPT: '採購入庫',
    SCRAP_OUT: '報廢出庫'
  };
  return map[type] || type || '-';
}

function reservationStatusLabel(status) {
  const map = { ACTIVE: '預留中', CONSUMED: '已扣庫存', RELEASED: '已釋放' };
  return map[status] || status || '-';
}

function sourceLabel(type, id) {
  if (!type) return '-';
  const map = {
    order_item: '訂單項目',
    work_order_line_item: '工單明細',
    purchase_request: '叫貨需求',
    manual: '手動',
    scrap: '報廢'
  };
  return `${map[type] || type} #${id}`;
}

function productCategory(item) {
  return item.category_info?.name || item.category || '未分類';
}

const activeCategories = computed(() => categories.value.filter(category => category.is_active));
const createModalTitle = computed(() => createItemType.value === 'PART' ? '新增零件' : '新增商品');

const InventoryTable = defineComponent({
  props: {
    items: { type: Array, required: true }
  },
  setup(props) {
    const stockValue = (value) => value === null || value === undefined ? '-' : formatNumber(value);
    return () => {
      const rows = props.items.length
        ? props.items.map(item => h('tr', { key: item.id, class: { 'low-stock': item.is_low_stock } }, [
          h('td', [h('strong', { class: 'product-name' }, item.name)]),
          h('td', productCategory(item)),
          h('td', { class: 'stock-cell' }, stockValue(item.stock)),
          h('td', { class: 'available-cell' }, stockValue(item.available_stock)),
          h('td', { class: 'reserved-cell' }, stockValue(item.reserved_stock))
        ]))
        : [h('tr', [h('td', { colspan: 5, class: 'empty-row' }, '尚無庫存資料。')])];

      return h('div', { class: 'inventory-table-block' }, [
        h('div', { class: 'table-wrap' }, [
          h('table', { class: 'data-table inventory-table' }, [
            h('thead', [
              h('tr', [
                h('th', '品項名稱'),
                h('th', '分類'),
                h('th', '實際庫存'),
                h('th', '可用庫存'),
                h('th', '預留數量')
              ])
            ]),
            h('tbody', rows)
          ])
        ])
      ]);
    };
  }
});

async function fetchItems() {
  const [shop, parts, all, low] = await Promise.all([
    getInventoryItems({ type: 'shop' }),
    getInventoryItems({ type: 'part' }),
    getInventoryItems({ type: 'all' }),
    getInventoryItems({ type: 'all', low_stock: true })
  ]);
  shopItems.value = shop;
  partItems.value = parts;
  allItems.value = all;
  lowStockItems.value = low;
  all.forEach(item => {
    const current = stocktakeDrafts[item.id];
    stocktakeDrafts[item.id] = {
      stock_after: current?.stock_after ?? item.stock ?? 0,
      reason: current?.reason || ''
    };
  });
}

async function fetchCategories() {
  categories.value = await getProductCategories();
}

async function fetchMovements() {
  movements.value = await getInventoryMovements();
}

async function fetchReservations() {
  reservations.value = await getInventoryReservations(reservationStatus.value ? { status: reservationStatus.value } : {});
}

async function fetchAll() {
  loading.value = true;
  try {
    await Promise.all([fetchItems(), fetchMovements(), fetchReservations(), fetchCategories()]);
  } catch (error) {
    alert(`載入庫存資料失敗：${error.response?.data?.detail || error.message}`);
  } finally {
    loading.value = false;
  }
}

function selectTab(tabKey) {
  const routeName = tabRouteMap[tabKey];
  if (routeName) {
    router.push({ name: routeName });
    return;
  }
  activeTab.value = tabKey;
}

function stocktakeDifference(item) {
  const counted = Number(stocktakeDrafts[item.id]?.stock_after ?? item.stock ?? 0);
  return counted - Number(item.stock || 0);
}

async function submitStocktake(item) {
  const draft = stocktakeDrafts[item.id];
  if (!draft || !draft.reason.trim()) {
    alert('請輸入盤點原因。');
    return;
  }
  savingAdjustmentId.value = item.id;
  try {
    await adjustInventory({
      product_id: item.id,
      stock_after: Number(draft.stock_after) || 0,
      reason: draft.reason,
      actor: adminUser.value?.full_name || adminUser.value?.username
    });
    await Promise.all([fetchItems(), fetchMovements()]);
  } catch (error) {
    alert(`盤點入帳失敗：${error.response?.data?.detail || error.message}`);
  } finally {
    savingAdjustmentId.value = null;
  }
}

function openCreateModal(inventoryType) {
  createItemType.value = inventoryType;
  Object.assign(createForm, defaultCreateForm(inventoryType));
  selectedCreateFile.value = null;
  showCreateModal.value = true;
}

function closeCreateModal() {
  showCreateModal.value = false;
  selectedCreateFile.value = null;
}

function onCreateFileChange(event) {
  selectedCreateFile.value = event.target.files?.[0] || null;
}

async function submitCreateItem() {
  savingCreate.value = true;
  try {
    const formData = new FormData();
    formData.append('name', createForm.name);
    formData.append('price', Number(createForm.price) || 0);
    formData.append('stock', Number(createForm.stock) || 0);
    formData.append('inventory_type', createForm.inventory_type);
    formData.append('low_stock_threshold', Number(createForm.low_stock_threshold) || 0);
    formData.append('description', createForm.description || '');
    if (createForm.category_id) formData.append('category_id', Number(createForm.category_id));
    else formData.append('category', '');
    if (selectedCreateFile.value) formData.append('file', selectedCreateFile.value);

    await createProduct(formData);
    closeCreateModal();
    await fetchItems();
  } catch (error) {
    alert(`新增失敗：${error.response?.data?.detail || error.message}`);
  } finally {
    savingCreate.value = false;
  }
}

function canReleaseReservation(reservation) {
  return reservation.status === 'ACTIVE' && reservation.source_type === 'work_order_line_item';
}

async function releaseReservation(reservation) {
  const reason = window.prompt(`請輸入取消預留原因：${reservation.product_name || `#${reservation.product_id}`}`);
  if (!reason) return;
  try {
    await releaseInventoryReservation(reservation.id, {
      reason,
      actor: adminUser.value?.full_name || adminUser.value?.username
    });
    await fetchAll();
  } catch (error) {
    alert(`取消預留失敗：${error.response?.data?.detail || error.message}`);
  }
}

async function submitScrap() {
  if (!scrapForm.product_id) return;
  savingScrap.value = true;
  try {
    await scrapInventory({
      product_id: Number(scrapForm.product_id),
      quantity: Number(scrapForm.quantity) || 1,
      reason: scrapForm.reason,
      actor: adminUser.value?.full_name || adminUser.value?.username
    });
    scrapForm.product_id = '';
    scrapForm.quantity = 1;
    scrapForm.reason = '';
    await fetchAll();
  } catch (error) {
    alert(`報廢出庫失敗：${error.response?.data?.detail || error.message}`);
  } finally {
    savingScrap.value = false;
  }
}

watch(
  () => route.meta.inventorySection,
  section => {
    if (routeTabMap[section]) activeTab.value = routeTabMap[section];
  }
);

onMounted(fetchAll);
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-inventory {
  color: #eef2f7;
}

.section-header,
.panel-title,
.tabs,
.adjust-form {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.section-header {
  margin-bottom: 18px;
}

.section-header h2,
.panel-title h3 {
  margin: 0;
}

.role-chip {
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 999px;
  padding: 6px 12px;
  color: #cbd5e1;
  background: rgba(15, 23, 42, 0.72);
}

.tabs {
  justify-content: flex-start;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.tabs button,
.btn {
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 6px;
  padding: 9px 14px;
  color: #e2e8f0;
  background: rgba(15, 23, 42, 0.78);
  cursor: pointer;
}

.tabs button.active,
.btn-primary {
  border-color: #38bdf8;
  color: #082f49;
  background: #38bdf8;
}

.btn-outline {
  background: transparent;
}

.panel {
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  padding: 18px;
  background: rgba(15, 23, 42, 0.54);
}

.inventory-panel {
  width: 100%;
}

.list-heading {
  margin-bottom: 16px;
}

.inventory-table-block :deep(.panel-title) {
  margin-bottom: 16px;
}

.inventory-table-block :deep(.table-wrap) {
  width: 100%;
  overflow-x: auto;
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  background-color: $dark-grey;
}

.table-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  background-color: $dark-grey;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid $medium-grey;
  padding: 0.8rem 0.9rem;
  text-align: left;
  vertical-align: middle;
  white-space: nowrap;
}

.data-table th {
  color: $text-secondary;
  background-color: $background-color;
  font-size: 0.82rem;
  font-weight: 700;
}

.data-table tbody tr:last-child td {
  border-bottom: 0;
}

.data-table tbody tr:hover {
  background-color: rgba($primary-color, 0.05);
}

.inventory-table-block :deep(.inventory-table) {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  table-layout: fixed;
}

.inventory-table-block :deep(.inventory-table th),
.inventory-table-block :deep(.inventory-table td) {
  padding: 0.8rem 0.9rem;
  border-bottom: 1px solid $medium-grey;
  text-align: left;
  vertical-align: middle;
  white-space: nowrap;
}

.inventory-table-block :deep(.inventory-table th) {
  color: $text-secondary;
  background-color: $background-color;
  font-size: 0.82rem;
  font-weight: 700;
}

.inventory-table-block :deep(.inventory-table tbody tr:last-child td) {
  border-bottom: 0;
}

.inventory-table-block :deep(.inventory-table tbody tr:hover) {
  background-color: rgba($primary-color, 0.05);
}

.inventory-table-block :deep(.inventory-table th:first-child) {
  width: 30%;
}

.inventory-table-block :deep(.inventory-table th:nth-child(2)) {
  width: 25%;
}

.inventory-table-block :deep(.inventory-table td) {
  overflow: hidden;
  text-overflow: ellipsis;
}

.inventory-table :deep(.product-name) {
  color: #ff5656;
  font-weight: 700;
}

.inventory-table :deep(.stock-cell),
.inventory-table :deep(.available-cell),
.inventory-table :deep(.reserved-cell) {
  font-weight: 700;
}

.positive {
  color: #86efac;
}

.negative {
  color: #fca5a5;
}

.inventory-table :deep(.low-stock .available-cell) {
  color: #ff5656;
}

.data-table .empty-row,
.inventory-table-block :deep(.empty-row) {
  padding: 2rem;
  color: $text-disabled;
  text-align: center;
}

.status-tag {
  border-radius: 999px;
  padding: 4px 9px;
  background: rgba(148, 163, 184, 0.16);
}

.status-tag.active {
  color: #7dd3fc;
}

.status-tag.consumed {
  color: #86efac;
}

.status-tag.released {
  color: #cbd5e1;
}

.empty-row {
  color: #94a3b8;
  text-align: center;
}

.adjust-form {
  align-items: flex-end;
  flex-wrap: wrap;
}

.panel-description,
.permission-note {
  margin: 6px 0 0;
  color: $text-secondary;
  font-size: 0.88rem;
}

.stocktake-wrap {
  margin-top: 16px;
}

.stocktake-table {
  min-width: 1120px;
}

.stocktake-table td:first-child {
  min-width: 180px;
}

.stocktake-table small {
  display: block;
  margin-top: 4px;
  color: $text-disabled;
}

.count-input {
  width: 96px;
}

.reason-input {
  width: 180px;
}

.adjust-form label {
  display: flex;
  flex: 1 1 220px;
  flex-direction: column;
  gap: 8px;
  color: #cbd5e1;
}

.reason-field {
  flex-basis: 100%;
}

input,
select,
textarea {
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 6px;
  padding: 10px 12px;
  color: #e2e8f0;
  background: rgba(2, 6, 23, 0.58);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.72);
}

.modal {
  width: min(680px, 100%);
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  padding: 20px;
  background: $dark-grey;
}

.modal-header,
.form-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.modal-header {
  margin-bottom: 18px;
}

.modal-header h3 {
  margin: 0;
}

.create-form,
.create-form label {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.create-form {
  gap: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.form-actions {
  justify-content: flex-end;
}

@media (max-width: 720px) {
  .section-header,
  .panel-title,
  .adjust-form {
    align-items: stretch;
    flex-direction: column;
  }

  .tabs button {
    flex: 1 1 46%;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

}
</style>
