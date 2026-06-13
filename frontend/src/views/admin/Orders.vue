<template>
  <div class="admin-orders">
    <div class="section-header">
      <h2>訂單管理</h2>
      <button class="btn btn-primary" @click="openCreateModal">＋ 新增現場訂單</button>
    </div>

    <!-- 篩選 -->
    <div class="filter-bar">
      <div class="search-wrap">
        <span class="icon">🔍</span>
        <input type="text" v-model="searchKeyword" placeholder="搜尋姓名/電話..." class="search-input" />
      </div>
      <div class="filter-buttons">
        <button v-for="s in statusOptions" :key="s.value" class="filter-btn" :class="{ active: filterStatus === s.value }" @click="filterStatus = s.value">
          {{ s.label }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else class="order-table-wrap">
      <table class="order-table">
        <thead>
          <tr>
            <th>訂單編號</th>
            <th>來源</th>
            <th>客戶類型</th>
            <th>客戶</th>
            <th>電話</th>
            <th>金額</th>
            <th>狀態</th>
            <th>建立時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="order in filteredOrders"
            :key="order.id"
            :class="{ canceled: order.status === 'CANCELED' }"
            class="order-row"
            @click="openDetailModal(order)"
          >
            <td>#{{ order.id }}</td>
            <td><span class="source-tag" :class="order.source">{{ order.source === 'instore' ? '現場' : '線上' }}</span></td>
            <td><span class="customer-tag" :class="getCustomerType(order)">{{ getCustomerType(order) === 'guest' ? '散客' : '會員' }}</span></td>
            <td>{{ order.recipient_name }}</td>
            <td>{{ order.recipient_phone }}</td>
            <td class="amount">NT$ {{ order.total_amount?.toLocaleString() }}</td>
            <td>
              <select v-model="order.status" @click.stop @change.stop="handleStatusChange(order)" class="status-select" :class="getStatusClass(order.status)">
                <option v-for="(label, key) in statusMap" :key="key" :value="key">{{ label }}</option>
              </select>
            </td>
            <td class="time">{{ formatDate(order.created_at) }}</td>
            <td class="actions">
              <button v-if="order.source === 'instore' && order.status !== 'CANCELED'" class="btn-icon" @click.stop="openEditModal(order)" title="編輯">✏️</button>
              <button v-if="getCustomerType(order) === 'guest'" class="btn-icon merge" @click.stop="openMergeModal(order)" title="合併到會員">⇄</button>
              <button v-if="order.status !== 'CANCELED'" class="btn-icon danger" @click.stop="handleCancel(order.id)" title="取消訂單">🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="filteredOrders.length === 0" class="empty">查無符合條件的訂單。</div>
    </div>

    <!-- 新增現場訂單 Modal -->
    <div class="modal-overlay" v-if="showCreateModal" @click.self="showCreateModal = false">
      <div class="modal">
        <h3>新增現場訂單</h3>
        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>客戶類型</label>
            <select v-model="createForm.customer_type" @change="onCustomerTypeChange">
              <option value="member">會員</option>
              <option value="guest">散客</option>
            </select>
          </div>
          <div class="form-group" v-if="createForm.customer_type === 'member'">
            <label>選擇會員</label>
            <select v-model="createForm.google_id" required @change="onMemberSelect">
              <option value="" disabled>請選擇會員</option>
              <option v-for="m in members" :key="m.google_id" :value="m.google_id">{{ m.name }} ({{ m.phone }})</option>
            </select>
          </div>
          <template v-else>
            <div class="form-group">
              <label>散客姓名</label>
              <input type="text" v-model.trim="createForm.guest_name" required />
            </div>
            <div class="form-group">
              <label>散客電話</label>
              <input type="text" v-model.trim="createForm.guest_phone" required />
            </div>
            <div class="form-group">
              <label>散客備註 (選填)</label>
              <textarea v-model="createForm.guest_notes" rows="2" placeholder="例如車款、習慣、來源"></textarea>
            </div>
          </template>
          <div class="form-group">
            <label>訂單金額 (NT$)</label>
            <input type="number" v-model.number="createForm.total_amount" required min="1" />
          </div>
          <div class="form-group">
            <label>備註 (選填)</label>
            <textarea v-model="createForm.notes" rows="2"></textarea>
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="showCreateModal = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              {{ submitting ? '處理中...' : '建立訂單' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 訂單詳情 Modal -->
    <div class="modal-overlay" v-if="showDetailModal" @click.self="showDetailModal = false">
      <div class="modal order-detail-modal">
        <div class="detail-header">
          <div>
            <h3>訂單詳情 #{{ selectedOrder?.id }}</h3>
            <p>{{ selectedOrder ? formatDate(selectedOrder.created_at) : '' }}</p>
          </div>
          <button type="button" class="btn-close" @click="showDetailModal = false">×</button>
        </div>

        <div v-if="selectedOrder" class="detail-content">
          <div class="detail-grid">
            <div>
              <span>客戶類型</span>
              <strong>{{ getCustomerType(selectedOrder) === 'guest' ? '散客' : '會員' }}</strong>
            </div>
            <div>
              <span>客戶</span>
              <strong>{{ selectedOrder.recipient_name }}</strong>
            </div>
            <div>
              <span>電話</span>
              <strong>{{ selectedOrder.recipient_phone }}</strong>
            </div>
            <div>
              <span>訂單狀態</span>
              <strong>{{ statusMap[selectedOrder.status] || selectedOrder.status }}</strong>
            </div>
            <div>
              <span>來源</span>
              <strong>{{ selectedOrder.source === 'instore' ? '現場' : '線上' }}</strong>
            </div>
            <div>
              <span>總金額</span>
              <strong>NT$ {{ selectedOrder.total_amount?.toLocaleString() }}</strong>
            </div>
          </div>

          <div v-if="selectedOrder.notes" class="detail-notes">
            <span>備註</span>
            <p>{{ selectedOrder.notes }}</p>
          </div>

          <div class="items-section">
            <h4>商品明細</h4>
            <div v-if="!selectedOrder.items || selectedOrder.items.length === 0" class="empty-items">
              此訂單尚無商品明細。
            </div>
            <table v-else class="items-table">
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
                <tr v-for="item in selectedOrder.items" :key="item.id">
                  <td>{{ item.product?.name || `商品 #${item.product_id}` }}</td>
                  <td>{{ item.quantity }}</td>
                  <td>NT$ {{ item.unit_price?.toLocaleString() }}</td>
                  <td>NT$ {{ (item.quantity * item.unit_price)?.toLocaleString() }}</td>
                  <td>
                    <select
                      v-model="item.status"
                      class="item-status-select"
                      :class="getItemStatusClass(item.status)"
                      :disabled="selectedOrder.status === 'COMPLETED'"
                      @change="handleItemStatusChange(selectedOrder, item)"
                    >
                      <option v-for="(label, key) in itemStatusMap" :key="key" :value="key">{{ label }}</option>
                    </select>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- 編輯現場訂單 Modal -->
    <div class="modal-overlay" v-if="showEditModal" @click.self="showEditModal = false">
      <div class="modal">
        <h3>編輯現場訂單 #{{ editForm.id }}</h3>
        <form @submit.prevent="handleEdit">
          <div class="form-group">
            <label>訂單金額 (NT$)</label>
            <input type="number" v-model.number="editForm.total_amount" required min="0" />
          </div>
          <div class="form-group">
            <label>客戶姓名</label>
            <input type="text" v-model="editForm.recipient_name" />
          </div>
          <div class="form-group">
            <label>電話</label>
            <input type="text" v-model="editForm.recipient_phone" />
          </div>
          <div class="form-group">
            <label>備註</label>
            <textarea v-model="editForm.notes" rows="2"></textarea>
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="showEditModal = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              {{ submitting ? '處理中...' : '更新訂單' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 散客合併 Modal -->
    <div class="modal-overlay" v-if="showMergeModal" @click.self="showMergeModal = false">
      <div class="modal">
        <h3>合併散客紀錄</h3>
        <form @submit.prevent="handleMerge">
          <div class="form-group">
            <label>散客</label>
            <input type="text" :value="`${mergeForm.guest_name} (${mergeForm.guest_phone})`" disabled />
          </div>
          <div class="form-group">
            <label>合併到會員</label>
            <select v-model="mergeForm.google_id" required>
              <option value="" disabled>請選擇會員</option>
              <option v-for="m in members" :key="m.google_id" :value="m.google_id">{{ m.name }} ({{ m.phone }})</option>
            </select>
          </div>
          <div class="merge-note">
            合併後，此散客所有訂單會轉到指定會員；已結案金額會補進會員累積消費。
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="showMergeModal = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              {{ submitting ? '處理中...' : '確認合併' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { getAllOrders, createInstoreOrder, updateOrderStatus, updateOrderItemStatus, updateInstoreOrder, cancelOrder, getMembers, mergeGuestToMember } from '../../api/admin';
import Swal from 'sweetalert2';

const orders = ref([]);
const members = ref([]);
const loading = ref(false);
const submitting = ref(false);
const searchKeyword = ref('');
const filterStatus = ref('');
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showMergeModal = ref(false);
const showDetailModal = ref(false);
const selectedOrder = ref(null);

const Toast = Swal.mixin({
  toast: true,
  position: 'top-end',
  showConfirmButton: false,
  timer: 3000,
  timerProgressBar: true,
  background: '#333',
  color: '#fff'
});

const statusMap = {
  'PENDING': '未付款',
  'DEPOSIT_PAID': '已付訂金',
  'FULL_PAID': '已付全款',
  'COMPLETED': '已結案',
  'CANCELED': '已取消'
};

const statusOptions = [
  { label: '全部', value: '' },
  { label: '未付款', value: 'PENDING' },
  { label: '已付訂金', value: 'DEPOSIT_PAID' },
  { label: '已付全款', value: 'FULL_PAID' },
  { label: '已結案', value: 'COMPLETED' },
  { label: '已取消', value: 'CANCELED' }
];

const itemStatusMap = {
  'NOT_ORDERED': '尚未訂貨',
  'ORDERED': '已訂貨',
  'ARRIVED_NEED_NOTIFY': '已到貨需通知',
  'NOTIFIED': '已通知',
  'COMPLETED': '已結案'
};

const emptyCreateForm = () => ({
  customer_type: 'member',
  google_id: '',
  guest_name: '',
  guest_phone: '',
  guest_notes: '',
  total_amount: 0,
  notes: '',
  recipient_name: '',
  recipient_phone: ''
});

const createForm = ref(emptyCreateForm());
const editForm = ref({ id: null, total_amount: 0, recipient_name: '', recipient_phone: '', notes: '' });
const mergeForm = ref({ guest_customer_id: null, guest_name: '', guest_phone: '', google_id: '' });

const filteredOrders = computed(() => {
  let list = orders.value;
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase();
    list = list.filter(o => (o.recipient_name || '').toLowerCase().includes(kw) || (o.recipient_phone || '').includes(kw));
  }
  if (filterStatus.value) list = list.filter(o => o.status === filterStatus.value);
  return list;
});

const getStatusClass = (status) => {
  if (status === 'CANCELED') return 'canceled';
  if (status === 'COMPLETED') return 'completed';
  if (status === 'PENDING') return 'unpaid';
  return 'partial';
};

const getItemStatusClass = (status) => {
  if (status === 'COMPLETED') return 'completed';
  if (status === 'NOTIFIED') return 'notified';
  if (status === 'ARRIVED_NEED_NOTIFY') return 'arrived';
  if (status === 'ORDERED') return 'ordered';
  return 'not-ordered';
};

const getCustomerType = (order) => order.customer_type || (order.guest_customer_id ? 'guest' : 'member');

const syncOrder = (updatedOrder) => {
  if (!updatedOrder?.id) return;
  const index = orders.value.findIndex(order => order.id === updatedOrder.id);
  if (index >= 0) {
    orders.value[index] = updatedOrder;
  }
  if (selectedOrder.value?.id === updatedOrder.id) {
    selectedOrder.value = updatedOrder;
  }
};

const formatDate = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
};

const fetchOrders = async () => {
  loading.value = true;
  try { orders.value = await getAllOrders(); }
  catch (e) { console.error(e); }
  finally { loading.value = false; }
};

const fetchMembers = async () => {
  try { members.value = (await getMembers()).filter(m => m.google_id !== 'system'); }
  catch (e) { console.error(e); }
};

const onCustomerTypeChange = () => {
  createForm.value.google_id = '';
  createForm.value.guest_name = '';
  createForm.value.guest_phone = '';
  createForm.value.guest_notes = '';
  createForm.value.recipient_name = '';
  createForm.value.recipient_phone = '';
};

const onMemberSelect = () => {
  const m = members.value.find(m => m.google_id === createForm.value.google_id);
  if (m) {
    createForm.value.recipient_name = m.name || '';
    createForm.value.recipient_phone = m.phone || '';
  }
};

const openCreateModal = () => {
  createForm.value = emptyCreateForm();
  showCreateModal.value = true;
};

const handleCreate = async () => {
  submitting.value = true;
  try {
    const payload = { ...createForm.value };
    if (payload.customer_type === 'guest') {
      payload.recipient_name = payload.guest_name;
      payload.recipient_phone = payload.guest_phone;
    }
    await createInstoreOrder(payload);
    Toast.fire({ icon: 'success', title: '現場訂單已建立！' });
    showCreateModal.value = false;
    fetchOrders();
  } catch (e) { 
    console.error(e); 
    Swal.fire('錯誤', '建立失敗：' + (e.response?.data?.detail || ''), 'error'); 
  }
  finally { submitting.value = false; }
};

const handleStatusChange = async (order) => {
  try {
    const updatedOrder = await updateOrderStatus(order.id, order.status);
    syncOrder(updatedOrder);
    Toast.fire({ icon: 'success', title: '狀態已更新' });
  } catch (e) {
    console.error(e);
    Swal.fire('錯誤', '狀態更新失敗', 'error');
    fetchOrders();
  }
};

const openDetailModal = (order) => {
  selectedOrder.value = order;
  showDetailModal.value = true;
};

const handleItemStatusChange = async (order, item) => {
  try {
    const updatedItem = await updateOrderItemStatus(item.id, item.status);
    const targetOrder = orders.value.find(o => o.id === order.id);
    const targetItem = targetOrder?.items?.find(i => i.id === item.id);
    if (targetItem) {
      Object.assign(targetItem, updatedItem);
    }
    if (selectedOrder.value?.id === order.id) {
      const selectedItem = selectedOrder.value.items?.find(i => i.id === item.id);
      if (selectedItem) {
        Object.assign(selectedItem, updatedItem);
      }
    }
    Toast.fire({ icon: 'success', title: '商品狀態已更新' });
  } catch (e) {
    console.error(e);
    Swal.fire('錯誤', e.response?.data?.detail || '商品狀態更新失敗', 'error');
    fetchOrders();
  }
};

const openEditModal = (order) => {
  editForm.value = {
    id: order.id,
    total_amount: order.total_amount,
    recipient_name: order.recipient_name,
    recipient_phone: order.recipient_phone,
    notes: order.notes || ''
  };
  showEditModal.value = true;
};

const openMergeModal = (order) => {
  mergeForm.value = {
    guest_customer_id: order.guest_customer_id,
    guest_name: order.guest_customer?.name || order.recipient_name,
    guest_phone: order.guest_customer?.phone || order.recipient_phone,
    google_id: ''
  };
  showMergeModal.value = true;
};

const handleMerge = async () => {
  if (!mergeForm.value.guest_customer_id || !mergeForm.value.google_id) return;

  const result = await Swal.fire({
    title: '確認合併散客紀錄？',
    text: '合併後，散客訂單會轉到指定會員，已結案金額會補進累積消費。',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#e53935',
    cancelButtonColor: '#616161',
    confirmButtonText: '確認合併',
    cancelButtonText: '取消',
    background: '#2a2a2a',
    color: '#fff'
  });

  if (!result.isConfirmed) return;

  submitting.value = true;
  try {
    const res = await mergeGuestToMember(mergeForm.value.guest_customer_id, mergeForm.value.google_id);
    Toast.fire({ icon: 'success', title: `已合併 ${res.moved_orders || 0} 筆訂單` });
    showMergeModal.value = false;
    fetchOrders();
    fetchMembers();
  } catch (e) {
    console.error(e);
    Swal.fire('錯誤', '合併失敗：' + (e.response?.data?.detail || ''), 'error');
  } finally {
    submitting.value = false;
  }
};

const handleEdit = async () => {
  submitting.value = true;
  try {
    await updateInstoreOrder(editForm.value.id, {
      total_amount: editForm.value.total_amount,
      recipient_name: editForm.value.recipient_name,
      recipient_phone: editForm.value.recipient_phone,
      notes: editForm.value.notes
    });
    Toast.fire({ icon: 'success', title: '訂單已更新！' });
    showEditModal.value = false;
    fetchOrders();
  } catch (e) { 
    console.error(e); 
    Swal.fire('錯誤', '更新失敗：' + (e.response?.data?.detail || ''), 'error'); 
  }
  finally { submitting.value = false; }
};

const handleCancel = async (id) => {
  const result = await Swal.fire({
    title: '確定要取消此訂單嗎？',
    text: "取消後，庫存將會自動恢復。",
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#e53935',
    cancelButtonColor: '#616161',
    confirmButtonText: '確定取消',
    cancelButtonText: '保留訂單',
    background: '#2a2a2a',
    color: '#fff'
  });

  if (result.isConfirmed) {
    try { 
      await cancelOrder(id); 
      Toast.fire({ icon: 'success', title: '訂單已取消' }); 
      fetchOrders(); 
    }
    catch (e) { 
      console.error(e); 
      Swal.fire('錯誤', '取消失敗', 'error'); 
    }
  }
};

onMounted(() => { fetchOrders(); fetchMembers(); });
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-orders {
  color: $text-primary;

  .section-header {
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;
    h2 { color: $primary-light; margin: 0; }

    @media (max-width: 768px) {
      flex-direction: column;
      align-items: stretch;
      gap: 1rem;
      margin-bottom: 1.5rem;

      h2 {
        background-color: rgba($primary-color, 0.1);
        padding: 0.8rem;
        border-radius: $border-radius;
        text-align: center;
        border-left: 4px solid $primary-color;
      }

      .btn {
        width: 100%;
      }
    }
  }

  .filter-bar {
    display: flex; justify-content: space-between; flex-wrap: wrap; margin-bottom: 1.5rem; align-items: center; gap: 1rem;
    
    .search-wrap {
      position: relative;
      .icon { position: absolute; left: 1rem; top: 50%; transform: translateY(-50%); opacity: 0.5; }
      .search-input {
        padding: 0.7rem 1rem 0.7rem 2.5rem; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 30px; color: $text-primary; font-size: 0.95rem; width: 250px; transition: $transition-base;
        &::placeholder { color: $text-disabled; }
        &:focus { outline: none; border-color: $primary-color; background: rgba(255, 255, 255, 0.1); box-shadow: 0 0 10px rgba($primary-color, 0.3); }
      }
    }
    
    .filter-buttons {
      display: flex; gap: 0.5rem; flex-wrap: wrap;
      .filter-btn {
        padding: 0.5rem 1rem; border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(255, 255, 255, 0.05);
        color: $text-secondary; border-radius: 20px; cursor: pointer; font-size: 0.85rem; transition: $transition-base;
        &.active { background: $primary-color; border-color: $primary-color; color: #fff; box-shadow: 0 4px 10px rgba($primary-color, 0.3); }
        &:hover:not(.active) { background: rgba(255, 255, 255, 0.1); color: #fff; }
      }
    }

    @media (max-width: 768px) {
      flex-direction: column;
      align-items: stretch;
      
      .search-wrap {
        width: 100%;
        .search-input {
          width: 100%;
        }
      }

      .filter-buttons {
        justify-content: center;
      }
    }
  }

  .loading, .empty { text-align: center; padding: 3rem; color: $text-disabled; }

  .order-table-wrap { 
    overflow-x: auto; 
    background: linear-gradient(145deg, #2a2a2a, #1f1f1f);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
  }

  .order-table {
    width: 100%; border-collapse: collapse;

    th, td { padding: 1rem; text-align: left; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
    th { color: $text-disabled; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; background: rgba(0,0,0,0.2); position: sticky; top: 0; z-index: 10; }
    td { font-size: 0.95rem; }

    tr { transition: $transition-base; }
    .order-row { cursor: pointer; }
    tr.canceled td { opacity: 0.4; }
    tr:hover { background: rgba(255, 255, 255, 0.05); }

    .source-tag {
      padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: bold;
      &.online { background: rgba(#2196f3, 0.15); color: #2196f3; border: 1px solid rgba(#2196f3, 0.3); }
      &.instore { background: rgba(#ff9800, 0.15); color: #ff9800; border: 1px solid rgba(#ff9800, 0.3); }
    }

    .customer-tag {
      padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: bold;
      &.member { background: rgba(#4caf50, 0.15); color: #4caf50; border: 1px solid rgba(#4caf50, 0.3); }
      &.guest { background: rgba($primary-color, 0.15); color: $primary-light; border: 1px solid rgba($primary-color, 0.35); }
    }

    .amount { color: $primary-light; font-weight: 800; }
    .time { color: $text-disabled; font-size: 0.85rem; white-space: nowrap; }

    .status-select {
      padding: 0.4rem 0.6rem; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1);
      border-radius: 6px; color: $text-primary; font-size: 0.85rem; cursor: pointer; font-weight: bold;
      transition: $transition-base;
      &:hover { border-color: rgba(255,255,255,0.3); }
      &.unpaid { border-color: #ff9800; color: #ff9800; }
      &.partial { border-color: #2196f3; color: #2196f3; }
      &.completed { border-color: #4caf50; color: #4caf50; }
      &.canceled { border-color: #ff6b6b; color: #ff6b6b; }
      
      option { background: $dark-grey; color: $text-primary; }
    }

    .actions { 
      display: flex; gap: 0.5rem; white-space: nowrap;
      .btn-icon {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
        width: 32px; height: 32px; border-radius: 6px; display: flex; align-items: center; justify-content: center;
        cursor: pointer; transition: $transition-base;
        &:hover { background: rgba(255,255,255,0.15); transform: translateY(-2px); }
        &.merge:hover { background: rgba($primary-color, 0.2); border-color: rgba($primary-color, 0.4); }
        &.danger:hover { background: rgba(#ff6b6b, 0.2); border-color: rgba(#ff6b6b, 0.4); }
      }
    }
  }

  .btn {
    padding: 0.35rem 0.7rem; border: 1px solid $primary-color; background: transparent;
    color: $primary-color; border-radius: $border-radius; cursor: pointer; font-size: 0.8rem; transition: all 0.2s;
    &:hover { background: $primary-color; color: #fff; }
  }
  .btn-primary {
    background: $primary-color; color: #fff; border: none; padding: 0.5rem 1.2rem; font-weight: bold;
    &:hover { background: $primary-dark; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }
  .btn-danger {
    border-color: #ff6b6b; color: #ff6b6b;
    &:hover { background: #ff6b6b; color: #fff; }
  }

  .modal-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.7); backdrop-filter: blur(5px); z-index: 1000;
    display: flex; justify-content: center; align-items: center;
  }
  .modal {
    background: linear-gradient(145deg, #2a2a2a, #1f1f1f); border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px; padding: 2.5rem; width: 500px;
    max-width: 90%; max-height: 90vh; overflow-y: auto;
    box-shadow: 0 15px 35px rgba(0,0,0,0.5);

    h3 { color: $primary-light; margin: 0 0 1.5rem; font-size: 1.5rem; }
    .form-group {
      margin-bottom: 1.5rem; display: flex; flex-direction: column; gap: 0.5rem;
      label { color: $text-secondary; font-weight: 600; font-size: 0.95rem; }
      input, textarea, select {
        padding: 0.8rem 1rem; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px; color: $text-primary; font-size: 1rem; transition: $transition-base;
        &:focus { outline: none; border-color: $primary-color; background: rgba(0,0,0,0.4); box-shadow: 0 0 10px rgba($primary-color, 0.2); }
        &:disabled { opacity: 0.75; cursor: not-allowed; }
      }
      select { cursor: pointer; option { background: $dark-grey; color: $text-primary; } }
    }
    .merge-note {
      color: $text-secondary; line-height: 1.6; font-size: 0.9rem;
      padding: 0.8rem 1rem; border: 1px solid rgba($primary-color, 0.25);
      border-radius: 8px; background: rgba($primary-color, 0.08);
    }

    &.order-detail-modal {
      width: 820px;
    }

    .detail-header {
      display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1.5rem;
      h3 { margin-bottom: 0.25rem; }
      p { color: $text-disabled; margin: 0; font-size: 0.9rem; }
      .btn-close {
        width: 36px; height: 36px; border-radius: 50%; border: 1px solid rgba(255,255,255,0.15);
        background: rgba(255,255,255,0.05); color: $text-primary; font-size: 1.5rem; line-height: 1;
        cursor: pointer; transition: $transition-base;
        &:hover { background: rgba(255,255,255,0.12); }
      }
    }

    .detail-grid {
      display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.8rem; margin-bottom: 1rem;
      div {
        padding: 0.8rem; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: rgba(0,0,0,0.18);
        span { display: block; color: $text-disabled; font-size: 0.8rem; margin-bottom: 0.35rem; }
        strong { color: $text-primary; font-size: 0.95rem; overflow-wrap: anywhere; }
      }
    }

    .detail-notes {
      padding: 0.9rem 1rem; border: 1px solid rgba($primary-color, 0.22); border-radius: 8px;
      background: rgba($primary-color, 0.07); margin-bottom: 1.2rem;
      span { display: block; color: $text-disabled; font-size: 0.85rem; margin-bottom: 0.35rem; }
      p { color: $text-secondary; margin: 0; line-height: 1.6; white-space: pre-wrap; }
    }

    .items-section {
      h4 { color: $primary-light; margin: 1.2rem 0 0.8rem; }
      .empty-items { color: $text-disabled; padding: 1.2rem; text-align: center; border: 1px dashed rgba(255,255,255,0.15); border-radius: 8px; }
    }

    .items-table {
      width: 100%; border-collapse: collapse; min-width: 640px;
      th, td { padding: 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.08); text-align: left; }
      th { color: $text-disabled; font-size: 0.82rem; background: rgba(0,0,0,0.16); }
      td { color: $text-primary; font-size: 0.9rem; }
    }

    .item-status-select {
      min-width: 150px; padding: 0.45rem 0.6rem; border-radius: 6px; background: rgba(0,0,0,0.24);
      color: $text-primary; border: 1px solid rgba(255,255,255,0.12); font-weight: 700;
      &.not-ordered { border-color: #ff9800; color: #ff9800; }
      &.ordered { border-color: #2196f3; color: #2196f3; }
      &.arrived { border-color: $primary-light; color: $primary-light; }
      &.notified { border-color: #9c27b0; color: #ce93d8; }
      &.completed { border-color: #4caf50; color: #4caf50; }
      &:disabled { opacity: 0.7; cursor: not-allowed; }
      option { background: $dark-grey; color: $text-primary; }
    }

    @media (max-width: 768px) {
      .detail-grid { grid-template-columns: 1fr; }
      .items-section { overflow-x: auto; }
    }

    .form-actions {
      display: flex; gap: 1rem; justify-content: flex-end; margin-top: 2rem;
      .btn-outline {
        padding: 0.7rem 1.5rem; background: transparent; border: 1px solid rgba(255,255,255,0.2);
        color: $text-secondary; border-radius: 30px; cursor: pointer; transition: $transition-base; font-weight: bold;
        &:hover { background: rgba(255,255,255,0.1); color: #fff; }
      }
      .btn-primary {
        padding: 0.7rem 1.5rem; background: $primary-color; color: #fff; border: none;
        border-radius: 30px; font-weight: bold; cursor: pointer; transition: $transition-base;
        box-shadow: 0 4px 10px rgba($primary-color, 0.4);
        &:hover:not(:disabled) { background: $primary-light; transform: translateY(-2px); box-shadow: 0 6px 15px rgba($primary-color, 0.6); }
        &:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }
      }
    }
  }
}
</style>
