<template>
  <div class="admin-accounting">
    <div class="section-header">
      <div>
        <h2>帳務管理</h2>
        <p>收款、退款、商城待收款與應付帳款</p>
      </div>
      <button class="btn btn-outline" type="button" @click="fetchAll">重新整理</button>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <section v-else-if="activeTab === 'receipts'" class="panel">
      <div class="panel-title">
        <h3>收款紀錄</h3>
      </div>
      <table v-if="receipts.length" class="accounting-table">
        <thead>
          <tr>
            <th>來源</th>
            <th>單號</th>
            <th>客戶</th>
            <th>金額</th>
            <th>付款方式</th>
            <th>付款時間</th>
            <th>操作者</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in receipts" :key="record.id">
            <td>{{ sourceMap[record.source_type] || record.source_type }}</td>
            <td>#{{ record.source_id }}</td>
            <td>{{ record.customer_name || '-' }}</td>
            <td class="amount">NT$ {{ formatNumber(record.amount) }}</td>
            <td>{{ record.method || '-' }}</td>
            <td>{{ formatDateTime(record.paid_at) }}</td>
            <td>{{ record.actor || '-' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">目前沒有收款紀錄。</div>
    </section>

    <section v-else-if="activeTab === 'refunds'" class="panel">
      <div class="panel-title">
        <h3>退款紀錄</h3>
      </div>
      <form v-if="canCreateRefund" class="inline-form" @submit.prevent="submitRefund">
        <label>
          來源
          <select v-model="refundForm.source_type">
            <option value="WORK_ORDER">工單</option>
            <option value="SHOP_ORDER">商城訂單</option>
          </select>
        </label>
        <label>
          單號
          <input v-model.number="refundForm.source_id" type="number" min="1" required />
        </label>
        <label>
          金額
          <input v-model.number="refundForm.amount" type="number" min="1" required />
        </label>
        <label>
          方式
          <input v-model.trim="refundForm.method" />
        </label>
        <label>
          原因
          <input v-model.trim="refundForm.reason" />
        </label>
        <button class="btn btn-primary" type="submit" :disabled="saving">新增退款</button>
      </form>
      <div v-else class="permission-note">僅最高級管理員可新增退款。</div>
      <table v-if="refunds.length" class="accounting-table">
        <thead>
          <tr>
            <th>來源</th>
            <th>單號</th>
            <th>客戶</th>
            <th>退款金額</th>
            <th>方式</th>
            <th>原因</th>
            <th>退款時間</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in refunds" :key="record.id">
            <td>{{ sourceMap[record.source_type] || record.source_type }}</td>
            <td>#{{ record.source_id }}</td>
            <td>{{ record.customer_name || '-' }}</td>
            <td class="amount negative">NT$ {{ formatNumber(record.amount) }}</td>
            <td>{{ record.method || '-' }}</td>
            <td>{{ record.reason || '-' }}</td>
            <td>{{ formatDateTime(record.refunded_at) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">目前沒有退款紀錄。</div>
    </section>

    <section v-else-if="activeTab === 'shop'" class="panel">
      <div class="panel-title">
        <h3>商城待收款</h3>
      </div>
      <table v-if="shopReceivables.length" class="accounting-table">
        <thead>
          <tr>
            <th>訂單</th>
            <th>客戶</th>
            <th>電話</th>
            <th>金額</th>
            <th>付款狀態</th>
            <th>建立時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in shopReceivables" :key="order.id">
            <td>#{{ order.id }}</td>
            <td>{{ order.recipient_name }}</td>
            <td>{{ order.recipient_phone }}</td>
            <td class="amount">NT$ {{ formatNumber(order.total_amount) }}</td>
            <td><span class="status-tag" :class="order.payment_status">{{ shopPaymentStatusMap[order.payment_status] }}</span></td>
            <td>{{ formatDateTime(order.created_at) }}</td>
            <td>
              <div class="row-actions">
                <select v-model="order.next_payment_status">
                  <option v-for="(label, value) in shopPaymentStatusMap" :key="value" :value="value">{{ label }}</option>
                </select>
                <input v-model.trim="order.payment_method" placeholder="付款方式" />
                <button class="btn text" type="button" @click="submitShopPaymentStatus(order)">更新</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">目前沒有商城待收款。</div>
    </section>

    <section v-else-if="activeTab === 'payables'" class="panel">
      <div class="panel-title">
        <h3>應付帳款</h3>
      </div>
      <form class="inline-form payable-form" @submit.prevent="submitPayable">
        <label>
          供應商
          <input v-model.trim="payableForm.supplier_name" required />
        </label>
        <label>
          標題
          <input v-model.trim="payableForm.title" required />
        </label>
        <label>
          金額
          <input v-model.number="payableForm.amount" type="number" min="1" required />
        </label>
        <label>
          到期日
          <input v-model="payableForm.due_date" type="date" />
        </label>
        <label>
          叫貨需求 ID
          <input v-model.number="payableForm.purchase_request_id" type="number" min="1" />
        </label>
        <button class="btn btn-primary" type="submit" :disabled="saving">新增應付</button>
      </form>
      <table v-if="payables.length" class="accounting-table">
        <thead>
          <tr>
            <th>供應商</th>
            <th>標題</th>
            <th>金額</th>
            <th>已付</th>
            <th>未付</th>
            <th>到期日</th>
            <th>狀態</th>
            <th>付款</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="payable in payables" :key="payable.id">
            <td>{{ payable.supplier_name }}</td>
            <td>
              <strong>{{ payable.title }}</strong>
              <small v-if="payable.purchase_request_id">叫貨 #{{ payable.purchase_request_id }}</small>
            </td>
            <td class="amount">NT$ {{ formatNumber(payable.amount) }}</td>
            <td>NT$ {{ formatNumber(payable.paid_amount) }}</td>
            <td>NT$ {{ formatNumber(payable.balance_amount) }}</td>
            <td>{{ formatDate(payable.due_date) }}</td>
            <td><span class="status-tag" :class="payable.status">{{ payableStatusMap[payable.status] }}</span></td>
            <td>
              <div class="row-actions">
                <input v-model.number="payable.payment_amount" type="number" min="1" :max="payable.balance_amount" placeholder="金額" />
                <input v-model.trim="payable.payment_method" placeholder="方式" />
                <button class="btn text" type="button" :disabled="payable.balance_amount <= 0" @click="submitPayablePayment(payable)">付款</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">目前沒有應付帳款。</div>
    </section>

    <section v-else class="panel">
      <div class="panel-title">
        <h3>付款紀錄</h3>
      </div>
      <table v-if="payablePayments.length" class="accounting-table">
        <thead>
          <tr>
            <th>應付帳款</th>
            <th>供應商</th>
            <th>金額</th>
            <th>方式</th>
            <th>付款時間</th>
            <th>操作者</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="payment in payablePayments" :key="payment.rowKey">
            <td>#{{ payment.payable_id }}</td>
            <td>{{ payment.supplier_name }}</td>
            <td class="amount">NT$ {{ formatNumber(payment.amount) }}</td>
            <td>{{ payment.method || '-' }}</td>
            <td>{{ formatDateTime(payment.paid_at) }}</td>
            <td>{{ payment.actor || '-' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">目前沒有應付付款紀錄。</div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { storeToRefs } from 'pinia';
import {
  addPayablePayment,
  createAccountingRefund,
  createPayable,
  getAccountingReceipts,
  getAccountingRefunds,
  getPayables,
  getShopReceivables,
  updateOrderPaymentStatus
} from '../../api/admin';
import { useAuthStore } from '../../store/auth';

const authStore = useAuthStore();
const { adminUser } = storeToRefs(authStore);
const canCreateRefund = computed(() => adminUser.value?.role === '最高級');

const tabs = [
  { key: 'receipts', label: '收款紀錄' },
  { key: 'refunds', label: '退款紀錄' },
  { key: 'shop', label: '商城待收款' },
  { key: 'payables', label: '應付帳款' },
  { key: 'payments', label: '付款紀錄' }
];

const sourceMap = {
  WORK_ORDER: '工單',
  SHOP_ORDER: '商城訂單',
  PAYABLE: '應付帳款'
};

const shopPaymentStatusMap = {
  PENDING: '待付款',
  VERIFYING: '付款確認中',
  PAID: '已付款',
  FAILED: '付款失敗',
  PARTIALLY_REFUNDED: '部分退款',
  REFUNDED: '已退款',
  CANCELED: '已取消'
};

const payableStatusMap = {
  UNPAID: '未付款',
  PARTIALLY_PAID: '部分付款',
  PAID: '已付款',
  CANCELED: '已取消'
};

const activeTab = ref('receipts');
const loading = ref(false);
const saving = ref(false);
const receipts = ref([]);
const refunds = ref([]);
const shopReceivables = ref([]);
const payables = ref([]);

const refundForm = reactive({
  source_type: 'WORK_ORDER',
  source_id: null,
  amount: null,
  method: '',
  reason: ''
});

const payableForm = reactive({
  supplier_name: '',
  title: '',
  amount: null,
  due_date: '',
  purchase_request_id: null
});

const payablePayments = computed(() => {
  return payables.value.flatMap(payable => (payable.payments || []).map(payment => ({
    ...payment,
    rowKey: `${payable.id}-${payment.id}`,
    supplier_name: payable.supplier_name
  }))).sort((a, b) => new Date(b.paid_at || 0) - new Date(a.paid_at || 0));
});

const decorateShopReceivables = (items) => {
  return items.map(order => ({
    ...order,
    next_payment_status: order.payment_status,
    payment_method: ''
  }));
};

const decoratePayables = (items) => {
  return items.map(payable => ({
    ...payable,
    payment_amount: payable.balance_amount > 0 ? payable.balance_amount : null,
    payment_method: ''
  }));
};

const fetchAll = async () => {
  loading.value = true;
  try {
    const [receiptData, refundData, shopData, payableData] = await Promise.all([
      getAccountingReceipts({ limit: 300 }),
      getAccountingRefunds({ limit: 300 }),
      getShopReceivables({ limit: 300 }),
      getPayables({ limit: 300 })
    ]);
    receipts.value = Array.isArray(receiptData) ? receiptData : [];
    refunds.value = Array.isArray(refundData) ? refundData : [];
    shopReceivables.value = decorateShopReceivables(Array.isArray(shopData) ? shopData : []);
    payables.value = decoratePayables(Array.isArray(payableData) ? payableData : []);
  } catch (error) {
    alert(error.response?.data?.detail || '載入帳務資料失敗');
  } finally {
    loading.value = false;
  }
};

const submitRefund = async () => {
  saving.value = true;
  try {
    await createAccountingRefund({
      source_type: refundForm.source_type,
      source_id: refundForm.source_id,
      amount: refundForm.amount,
      method: refundForm.method || null,
      reason: refundForm.reason || null
    });
    refundForm.source_id = null;
    refundForm.amount = null;
    refundForm.method = '';
    refundForm.reason = '';
    await fetchAll();
  } catch (error) {
    alert(error.response?.data?.detail || '新增退款失敗');
  } finally {
    saving.value = false;
  }
};

const submitShopPaymentStatus = async (order) => {
  saving.value = true;
  try {
    await updateOrderPaymentStatus(order.id, {
      payment_status: order.next_payment_status,
      method: order.payment_method || null
    });
    await fetchAll();
  } catch (error) {
    alert(error.response?.data?.detail || '更新商城付款狀態失敗');
  } finally {
    saving.value = false;
  }
};

const submitPayable = async () => {
  saving.value = true;
  try {
    await createPayable({
      supplier_name: payableForm.supplier_name,
      title: payableForm.title,
      amount: payableForm.amount,
      due_date: payableForm.due_date ? `${payableForm.due_date}T00:00:00` : null,
      purchase_request_id: payableForm.purchase_request_id || null
    });
    payableForm.supplier_name = '';
    payableForm.title = '';
    payableForm.amount = null;
    payableForm.due_date = '';
    payableForm.purchase_request_id = null;
    await fetchAll();
  } catch (error) {
    alert(error.response?.data?.detail || '新增應付帳款失敗');
  } finally {
    saving.value = false;
  }
};

const submitPayablePayment = async (payable) => {
  saving.value = true;
  try {
    await addPayablePayment(payable.id, {
      amount: payable.payment_amount,
      method: payable.payment_method || null
    });
    await fetchAll();
  } catch (error) {
    alert(error.response?.data?.detail || '新增應付付款失敗');
  } finally {
    saving.value = false;
  }
};

const formatNumber = (value) => Number(value || 0).toLocaleString();

const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`;
};

const formatDateTime = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return `${formatDate(value)} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

onMounted(fetchAll);
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-accounting {
  color: $text-primary;
}

.section-header,
.tabs,
.panel-title,
.row-actions,
.inline-form {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.section-header,
.panel-title {
  justify-content: space-between;
}

.section-header {
  margin-bottom: 1.5rem;

  h2,
  p {
    margin: 0;
  }

  h2 {
    color: $primary-light;
  }

  p {
    color: $text-secondary;
    margin-top: 0.35rem;
  }
}

.tabs {
  flex-wrap: wrap;
  margin-bottom: 1rem;

  button {
    border: 1px solid rgba($primary-light, 0.35);
    border-radius: 6px;
    padding: 0.65rem 0.95rem;
    color: $text-primary;
    background: rgba($background-color, 0.72);
    cursor: pointer;

    &.active {
      color: $background-color;
      background: $primary-light;
    }
  }
}

.panel {
  border: 1px solid $medium-grey;
  border-radius: $border-radius;
  padding: 1rem;
  overflow: auto;
  background-color: $dark-grey;
}

.panel-title {
  margin-bottom: 1rem;

  h3 {
    margin: 0;
  }
}

.inline-form {
  align-items: flex-end;
  flex-wrap: wrap;
  margin-bottom: 1rem;

  label {
    display: flex;
    min-width: 150px;
    flex: 1 1 150px;
    flex-direction: column;
    gap: 0.35rem;
    color: $text-secondary;
  }

  &.payable-form label {
    min-width: 170px;
  }
}

.accounting-table {
  width: 100%;
  min-width: 840px;
  border-collapse: collapse;

  th,
  td {
    border-bottom: 1px solid $medium-grey;
    padding: 0.85rem 1rem;
    text-align: left;
    vertical-align: middle;
    white-space: nowrap;
  }

  th {
    color: $text-secondary;
    background-color: $background-color;
    font-size: 0.9rem;
    font-weight: 700;
  }

  .amount {
    color: $primary-light;
    font-weight: 700;

    &.negative {
      color: #fca5a5;
    }
  }

  strong,
  small {
    display: block;
  }

  small {
    color: $text-secondary;
    margin-top: 0.25rem;
  }
}

.row-actions {
  flex-wrap: wrap;

  input,
  select {
    max-width: 140px;
  }
}

.btn {
  border: 1px solid rgba($primary-light, 0.35);
  border-radius: 6px;
  padding: 0.55rem 0.8rem;
  color: $text-primary;
  background: rgba($background-color, 0.72);
  cursor: pointer;

  &.btn-primary {
    color: $background-color;
    background: $primary-light;
  }

  &.btn-outline {
    background: transparent;
  }

  &.text {
    border-color: transparent;
    color: $primary-light;
    background: transparent;
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
}

input,
select {
  border: 1px solid $medium-grey;
  border-radius: 6px;
  padding: 0.55rem 0.65rem;
  color: $text-primary;
  background: $background-color;
}

.status-tag {
  display: inline-flex;
  border-radius: 999px;
  padding: 0.25rem 0.55rem;
  background-color: rgba($medium-grey, 0.4);

  &.PENDING,
  &.UNPAID,
  &.VERIFYING {
    color: #facc15;
    background-color: rgba(#facc15, 0.15);
  }

  &.FAILED,
  &.REFUNDED,
  &.CANCELED {
    color: #fca5a5;
    background-color: rgba(#fca5a5, 0.14);
  }

  &.PARTIALLY_REFUNDED,
  &.PARTIALLY_PAID {
    color: #fb923c;
    background-color: rgba(#fb923c, 0.14);
  }

  &.PAID {
    color: #86efac;
    background-color: rgba(#86efac, 0.14);
  }
}

.loading,
.empty-state {
  padding: 3rem;
  text-align: center;
  color: $text-disabled;
}

@media (max-width: 760px) {
  .section-header,
  .panel-title,
  .inline-form {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
