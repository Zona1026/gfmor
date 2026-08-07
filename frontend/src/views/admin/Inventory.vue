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
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <section v-if="activeTab === 'shop'" class="panel">
      <InventoryTable title="商品庫存" :items="shopItems" :can-manage="canManageInventory" />
    </section>

    <section v-if="activeTab === 'parts'" class="panel">
      <InventoryTable title="零件 / 耗材庫存" :items="partItems" :can-manage="canManageInventory" />
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
              <th v-if="canManageInventory">異動前</th>
              <th v-if="canManageInventory">異動後</th>
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
              <td v-if="canManageInventory">{{ formatNumber(movement.stock_before) }}</td>
              <td v-if="canManageInventory">{{ formatNumber(movement.stock_after) }}</td>
              <td>{{ sourceLabel(movement.source_type, movement.source_id) }}</td>
              <td>{{ movement.reason || '-' }}</td>
            </tr>
            <tr v-if="movements.length === 0">
              <td :colspan="canManageInventory ? 8 : 6" class="empty-row">尚無庫存異動。</td>
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

    <section v-if="activeTab === 'adjust' && canUseCriticalInventory" class="panel">
      <div class="panel-title">
        <h3>手動調整庫存</h3>
      </div>
      <form class="adjust-form" @submit.prevent="submitAdjustment">
        <label>
          品項
          <select v-model.number="adjustmentForm.product_id" required @change="syncAdjustmentStock">
            <option value="">請選擇品項</option>
            <option v-for="item in allItems" :key="item.id" :value="item.id">
              {{ item.name }} / 目前 {{ formatNumber(item.stock) }}
            </option>
          </select>
        </label>
        <label>
          調整後實際庫存
          <input v-model.number="adjustmentForm.stock_after" type="number" min="0" required />
        </label>
        <label class="reason-field">
          原因
          <textarea v-model.trim="adjustmentForm.reason" rows="3" required></textarea>
        </label>
        <button class="btn btn-primary" type="submit" :disabled="savingAdjustment">
          {{ savingAdjustment ? '儲存中...' : '儲存調整' }}
        </button>
      </form>
      <div class="panel-title sub-title">
        <h3>報廢出庫</h3>
      </div>
      <form class="adjust-form" @submit.prevent="submitScrap">
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

    <section v-if="activeTab === 'low'" class="panel">
      <InventoryTable title="低庫存提醒" :items="lowStockItems" :can-manage="canManageInventory" />
    </section>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, reactive, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useAuthStore } from '../../store/auth';
import {
  adjustInventory,
  getInventoryItems,
  getInventoryMovements,
  getInventoryReservations,
  releaseInventoryReservation,
  scrapInventory
} from '../../api/admin';

const authStore = useAuthStore();
const { adminUser } = storeToRefs(authStore);

const managerRoles = ['最高級', '管理層'];
const canManageInventory = computed(() => managerRoles.includes(adminUser.value?.role));
const canUseCriticalInventory = computed(() => adminUser.value?.role === '最高級');

const activeTab = ref('shop');
const loading = ref(false);
const savingAdjustment = ref(false);
const savingScrap = ref(false);
const shopItems = ref([]);
const partItems = ref([]);
const allItems = ref([]);
const lowStockItems = ref([]);
const movements = ref([]);
const reservations = ref([]);
const reservationStatus = ref('');

const adjustmentForm = reactive({
  product_id: '',
  stock_after: 0,
  reason: ''
});

const scrapForm = reactive({
  product_id: '',
  quantity: 1,
  reason: ''
});

const tabs = [
  { key: 'shop', label: '商品庫存' },
  { key: 'parts', label: '零件 / 耗材庫存' },
  { key: 'movements', label: '庫存異動紀錄' },
  { key: 'reservations', label: '庫存預留紀錄' },
  { key: 'adjust', label: '手動調整 / 報廢', superOnly: true },
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

const InventoryTable = defineComponent({
  props: {
    title: { type: String, required: true },
    items: { type: Array, required: true },
    canManage: { type: Boolean, default: false }
  },
  setup(props) {
    const stockValue = (value) => value === null || value === undefined ? '-' : formatNumber(value);
    return () => h('div', { class: 'inventory-table-block' }, [
      h('div', { class: 'panel-title' }, [
        h('h3', props.title)
      ]),
      props.items.length
        ? h('div', { class: 'inventory-scroll' }, [
          h('div', { class: 'inventory-list' }, [
            h('div', { class: 'inventory-row inventory-head' }, [
              h('span', '商品名稱'),
              h('span', '商品分類'),
              h('span', '實際庫存'),
              h('span', '可用庫存'),
              h('span', '預留數量')
            ]),
            ...props.items.map(item => h('div', { key: item.id, class: { 'inventory-row': true, 'low-stock': item.is_low_stock } }, [
              h('strong', { class: 'product-name' }, item.name),
              h('span', { class: 'category-name' }, productCategory(item)),
              h('span', { class: 'stock-cell' }, stockValue(item.stock)),
              h('span', { class: 'available-cell' }, stockValue(item.available_stock)),
              h('span', { class: 'reserved-cell' }, stockValue(item.reserved_stock))
            ]))
          ])
        ])
        : h('p', { class: 'empty-row' }, '尚無庫存資料。')
    ]);
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
    await Promise.all([fetchItems(), fetchMovements(), fetchReservations()]);
  } catch (error) {
    alert(`載入庫存資料失敗：${error.response?.data?.detail || error.message}`);
  } finally {
    loading.value = false;
  }
}

function syncAdjustmentStock() {
  const item = allItems.value.find(entry => entry.id === Number(adjustmentForm.product_id));
  adjustmentForm.stock_after = item?.stock || 0;
}

async function submitAdjustment() {
  if (!adjustmentForm.product_id) return;
  savingAdjustment.value = true;
  try {
    await adjustInventory({
      product_id: Number(adjustmentForm.product_id),
      stock_after: Number(adjustmentForm.stock_after) || 0,
      reason: adjustmentForm.reason,
      actor: adminUser.value?.full_name || adminUser.value?.username
    });
    adjustmentForm.product_id = '';
    adjustmentForm.stock_after = 0;
    adjustmentForm.reason = '';
    await fetchAll();
  } catch (error) {
    alert(`調整庫存失敗：${error.response?.data?.detail || error.message}`);
  } finally {
    savingAdjustment.value = false;
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

.table-wrap {
  width: 100%;
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  padding: 12px 10px;
  text-align: left;
  white-space: nowrap;
}

.data-table th {
  color: #94a3b8;
  font-weight: 600;
}

.inventory-table-block :deep(.inventory-scroll) {
  display: inline-block;
  width: auto;
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  margin-top: 16px;
  background: #1f1f1f;
}

.inventory-table-block :deep(.inventory-list) {
  display: block;
  width: 860px;
  max-width: 100%;
  margin: 0;
}

.inventory-table-block :deep(.inventory-row) {
  display: grid;
  grid-template-columns: 220px 160px 110px 110px 110px;
  align-items: center;
  gap: 14px;
  min-height: 78px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.11);
  padding: 18px 20px;
  background: #202020;
}

.inventory-table-block :deep(.inventory-row:last-child) {
  border-bottom: 0;
}

.inventory-table-block :deep(.inventory-row strong),
.inventory-table-block :deep(.inventory-row span) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.inventory-table-block :deep(.inventory-head) {
  min-height: 74px;
  color: #f8fafc;
  font-size: 19px;
  font-weight: 800;
  background: #101010;
}

.inventory-table-block :deep(.inventory-head span) {
  color: #f8fafc;
}

.inventory-table-block :deep(.product-name) {
  color: #ff5656;
  font-size: 22px;
  font-weight: 800;
}

.inventory-table-block :deep(.category-name),
.inventory-table-block :deep(.stock-cell),
.inventory-table-block :deep(.reserved-cell) {
  color: #f8fafc;
  font-size: 20px;
  font-weight: 700;
}

.inventory-table-block :deep(.available-cell) {
  color: #f8fafc;
  font-size: 20px;
  font-weight: 700;
}

.positive {
  color: #86efac;
}

.negative {
  color: #fca5a5;
}

.inventory-table-block :deep(.low-stock .available-cell) {
  color: #ff5656;
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

  .inventory-table-block :deep(.inventory-list) {
    width: 760px;
    max-width: none;
  }

}
</style>
