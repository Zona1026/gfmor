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
        @click="setActiveTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <section v-else-if="activeTab === 'daily'" class="panel report-panel">
      <div class="panel-title report-heading">
        <div>
          <h3>日報表</h3>
          <p>彙整單日收款、退款與應付付款。</p>
        </div>
        <label class="report-period-control">
          報表日期
          <input v-model="selectedDailyDate" type="date" />
        </label>
      </div>
      <div class="report-summary-grid">
        <div class="report-summary-item income"><span>收款</span><strong>NT$ {{ formatNumber(dailySummary.income) }}</strong></div>
        <div class="report-summary-item refund"><span>退款</span><strong>NT$ {{ formatNumber(dailySummary.refunds) }}</strong></div>
        <div class="report-summary-item expense"><span>應付付款</span><strong>NT$ {{ formatNumber(dailySummary.expenses) }}</strong></div>
        <div class="report-summary-item net"><span>當日淨額</span><strong>NT$ {{ formatNumber(dailySummary.net) }}</strong></div>
      </div>
      <table v-if="dailyTransactions.length" class="accounting-table report-table">
        <thead><tr><th>時間</th><th>類型</th><th>來源</th><th>操作者</th><th>金額</th></tr></thead>
        <tbody>
          <tr v-for="record in dailyTransactions" :key="record.key">
            <td>{{ formatTaipeiDateTime(record.occurredAt) }}</td>
            <td>{{ record.typeLabel }}</td>
            <td>{{ record.sourceLabel }}</td>
            <td>{{ record.actor || '-' }}</td>
            <td class="amount" :class="{ negative: record.direction === 'out' }">
              {{ record.direction === 'out' ? '-' : '' }}NT$ {{ formatNumber(record.amount) }}
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">這一天沒有帳務紀錄。</div>
    </section>

    <section v-else-if="activeTab === 'monthly'" class="panel report-panel">
      <div class="panel-title report-heading">
        <div>
          <h3>月報表</h3>
          <p>按日彙整指定月份的收入與支出。</p>
        </div>
        <label class="report-period-control">
          報表月份
          <input v-model="selectedMonth" type="month" />
        </label>
      </div>
      <div class="report-summary-grid">
        <div class="report-summary-item income"><span>收款</span><strong>NT$ {{ formatNumber(monthlySummary.income) }}</strong></div>
        <div class="report-summary-item refund"><span>退款</span><strong>NT$ {{ formatNumber(monthlySummary.refunds) }}</strong></div>
        <div class="report-summary-item expense"><span>應付付款</span><strong>NT$ {{ formatNumber(monthlySummary.expenses) }}</strong></div>
        <div class="report-summary-item net"><span>當月淨額</span><strong>NT$ {{ formatNumber(monthlySummary.net) }}</strong></div>
      </div>
      <table v-if="monthlyDailyRows.length" class="accounting-table report-table">
        <thead><tr><th>日期</th><th>收款</th><th>退款</th><th>應付付款</th><th>淨額</th></tr></thead>
        <tbody>
          <tr v-for="row in monthlyDailyRows" :key="row.date">
            <td>{{ row.date.replaceAll('-', '/') }}</td>
            <td class="amount">NT$ {{ formatNumber(row.income) }}</td>
            <td class="amount negative">NT$ {{ formatNumber(row.refunds) }}</td>
            <td class="amount negative">NT$ {{ formatNumber(row.expenses) }}</td>
            <td class="amount" :class="{ negative: row.net < 0 }">NT$ {{ formatNumber(row.net) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">這個月份沒有帳務紀錄。</div>
    </section>

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
            <td>{{ formatTaipeiDateTime(record.paid_at) }}</td>
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
            <option value="SHOP_ORDER">商城訂單</option>
          </select>
        </label>
        <label>
          單號
          <input v-model.number="refundForm.source_id" type="number" min="1" required />
        </label>
        <label>
          金額
          <input v-model.number="refundForm.amount" type="number" min="1" :max="refundLookup.maxRefundAmount || null" required />
        </label>
        <label>
          方式
          <input v-model.trim="refundForm.method" />
        </label>
        <label>
          原因
          <input v-model.trim="refundForm.reason" />
        </label>
        <button
          class="btn btn-primary"
          type="submit"
          :disabled="saving || refundLookup.loading || !refundLookup.record || refundLookup.maxRefundAmount <= 0"
        >
          新增退款
        </button>
      </form>
      <div v-if="canCreateRefund" class="permission-note">工單退款請至「工單管理」的工單詳情操作。</div>
      <div v-if="canCreateRefund" class="lookup-state">
        <span v-if="refundLookup.loading">查詢單據中...</span>
        <span v-else-if="refundLookup.error" class="error-text">{{ refundLookup.error }}</span>
        <span v-else-if="refundLookup.record">
          {{ refundLookup.record.customer_name }} / 原金額 NT$ {{ formatNumber(refundLookup.record.total_amount) }} /
          已退 NT$ {{ formatNumber(refundLookup.refundedAmount) }} /
          可退 NT$ {{ formatNumber(refundLookup.maxRefundAmount) }}
        </span>
      </div>
      <div v-else class="permission-note">僅最高級管理員可新增退款。</div>
      <table v-if="refunds.length" class="accounting-table">
        <thead>
          <tr>
            <th>來源</th>
            <th>單號</th>
            <th>客戶</th>
            <th>退款金額</th>
            <th>退款類型</th>
            <th>庫存處理</th>
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
            <td>{{ refundTypeMap[record.refund_type] || record.refund_type }}</td>
            <td>{{ inventoryActionMap[record.inventory_action] || record.inventory_action }}</td>
            <td>{{ record.method || '-' }}</td>
            <td>{{ record.reason || '-' }}</td>
            <td>{{ formatTaipeiDateTime(record.refunded_at) }}</td>
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
            <th v-if="canManageAccounting">操作</th>
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
            <td v-if="canManageAccounting">
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
      <form v-if="canManageAccounting" class="inline-form payable-form" @submit.prevent="submitPayable">
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
            <th v-if="canManageAccounting">付款</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="payable in payables" :key="payable.id">
            <td>{{ payable.supplier_name }}</td>
            <td v-if="canManageAccounting">
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
            <td>{{ formatTaipeiDateTime(payment.paid_at) }}</td>
            <td>{{ payment.actor || '-' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">目前沒有應付付款紀錄。</div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import {
  addPayablePayment,
  createAccountingRefund,
  createPayable,
  getAccountingReceipts,
  getAccountingRefunds,
  getAllOrders,
  getPayables,
  getShopReceivables,
  getWorkOrder,
  updateOrderPaymentStatus
} from '../../api/admin';
import { useAuthStore } from '../../store/auth';
import { formatTaipeiDateTime } from '../../utils/dateTime';

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();
const { adminUser } = storeToRefs(authStore);
const canCreateRefund = computed(() => adminUser.value?.role === '最高級');
const canManageAccounting = computed(() => adminUser.value?.role === '最高級');

const tabs = [
  { key: 'daily', label: '日報表' },
  { key: 'monthly', label: '月報表' },
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

const refundTypeMap = {
  PARTIAL: '部分退款',
  PRICE_DIFFERENCE: '退差價',
  FULL: '整單退款'
};

const inventoryActionMap = {
  NO_CHANGE: '不調整',
  RESTOCK_ALL: '全部回補'
};

const reportTabs = ['daily', 'monthly'];
const initialReportTab = reportTabs.includes(route.query.report) ? route.query.report : 'receipts';
const activeTab = ref(initialReportTab);
const loading = ref(false);
const saving = ref(false);
const receipts = ref([]);
const refunds = ref([]);
const shopReceivables = ref([]);
const payables = ref([]);
const taipeiDateFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Taipei',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit'
});
const currentTaipeiDate = taipeiDateFormatter.format(new Date());
const selectedDailyDate = ref(currentTaipeiDate);
const selectedMonth = ref(currentTaipeiDate.slice(0, 7));

const refundForm = reactive({
  source_type: 'SHOP_ORDER',
  source_id: null,
  amount: null,
  method: '',
  reason: ''
});
const refundLookup = reactive({
  loading: false,
  error: '',
  record: null,
  refundedAmount: 0,
  maxRefundAmount: 0
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

const toTaipeiDateKey = (value) => {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : taipeiDateFormatter.format(date);
};

const accountingTransactions = computed(() => {
  const receiptRows = receipts.value.map(record => ({
    key: `receipt-${record.id}`,
    occurredAt: record.paid_at,
    type: 'income',
    typeLabel: '收款',
    sourceLabel: `${sourceMap[record.source_type] || record.source_type} #${record.source_id}`,
    actor: record.actor,
    amount: Number(record.amount || 0),
    direction: 'in'
  }));
  const refundRows = refunds.value.map(record => ({
    key: `refund-${record.id}`,
    occurredAt: record.refunded_at,
    type: 'refund',
    typeLabel: '退款',
    sourceLabel: `${sourceMap[record.source_type] || record.source_type} #${record.source_id}`,
    actor: record.actor,
    amount: Number(record.amount || 0),
    direction: 'out'
  }));
  const payableRows = payablePayments.value.map(record => ({
    key: `payable-payment-${record.rowKey}`,
    occurredAt: record.paid_at,
    type: 'expense',
    typeLabel: '應付付款',
    sourceLabel: `${record.supplier_name || '供應商'} / 應付 #${record.payable_id}`,
    actor: record.actor,
    amount: Number(record.amount || 0),
    direction: 'out'
  }));

  return [...receiptRows, ...refundRows, ...payableRows]
    .filter(record => record.occurredAt)
    .sort((a, b) => new Date(b.occurredAt) - new Date(a.occurredAt));
});

const summarizeTransactions = (records) => {
  const summary = records.reduce((total, record) => {
    total[record.type] += record.amount;
    return total;
  }, { income: 0, refund: 0, expense: 0 });
  return {
    income: summary.income,
    refunds: summary.refund,
    expenses: summary.expense,
    net: summary.income - summary.refund - summary.expense
  };
};

const dailyTransactions = computed(() => accountingTransactions.value.filter(record => {
  return toTaipeiDateKey(record.occurredAt) === selectedDailyDate.value;
}));
const dailySummary = computed(() => summarizeTransactions(dailyTransactions.value));
const monthlyTransactions = computed(() => accountingTransactions.value.filter(record => {
  return toTaipeiDateKey(record.occurredAt).startsWith(selectedMonth.value);
}));
const monthlySummary = computed(() => summarizeTransactions(monthlyTransactions.value));
const monthlyDailyRows = computed(() => {
  const grouped = new Map();
  monthlyTransactions.value.forEach(record => {
    const date = toTaipeiDateKey(record.occurredAt);
    if (!grouped.has(date)) grouped.set(date, []);
    grouped.get(date).push(record);
  });
  return [...grouped.entries()]
    .map(([date, records]) => ({ date, ...summarizeTransactions(records) }))
    .sort((a, b) => b.date.localeCompare(a.date));
});

const setActiveTab = (tab) => {
  activeTab.value = tab;
  const query = { ...route.query };
  if (reportTabs.includes(tab)) query.report = tab;
  else delete query.report;
  router.replace({ path: route.path, query });
};

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

const resetRefundLookup = () => {
  refundLookup.loading = false;
  refundLookup.error = '';
  refundLookup.record = null;
  refundLookup.refundedAmount = 0;
  refundLookup.maxRefundAmount = 0;
};

const refundedTotalFor = (sourceType, sourceId) => {
  const targetId = Number(sourceId);
  return refunds.value
    .filter(record => record.source_type === sourceType && Number(record.source_id) === targetId)
    .reduce((total, record) => total + Number(record.amount || 0), 0);
};

const latestPaymentMethodFor = (sourceType, sourceId) => {
  const targetId = Number(sourceId);
  const receipt = receipts.value.find(record => {
    return record.source_type === sourceType && Number(record.source_id) === targetId && record.method;
  });
  return receipt?.method || '';
};

const buildRefundLookupRecord = (sourceType, record) => {
  if (sourceType === 'WORK_ORDER') {
    return {
      customer_name: record.customer_name || '-',
      total_amount: Math.max(Number(record.paid_amount || 0), Number(record.total_amount || 0)),
      payment_status: record.payment_status
    };
  }

  return {
    customer_name: record.recipient_name || '-',
    total_amount: Number(record.total_amount || 0),
    payment_status: record.payment_status
  };
};

const lookupRefundSource = async () => {
  const sourceId = Number(refundForm.source_id);
  if (!sourceId || sourceId < 1) {
    resetRefundLookup();
    return;
  }

  const sourceType = refundForm.source_type;
  refundLookup.loading = true;
  refundLookup.error = '';

  try {
    const sourceRecord = sourceType === 'WORK_ORDER'
      ? await getWorkOrder(sourceId)
      : (await getAllOrders({ source: 'online' })).find(order => Number(order.id) === sourceId);

    if (!sourceRecord) {
      resetRefundLookup();
      refundLookup.error = sourceType === 'WORK_ORDER' ? '找不到此工單' : '找不到此商城訂單';
      return;
    }

    const record = buildRefundLookupRecord(sourceType, sourceRecord);
    const refundedAmount = refundedTotalFor(sourceType, sourceId);
    const maxRefundAmount = Math.max(0, Number(record.total_amount || 0) - refundedAmount);

    refundLookup.record = record;
    refundLookup.refundedAmount = refundedAmount;
    refundLookup.maxRefundAmount = maxRefundAmount;
    refundForm.amount = maxRefundAmount > 0 ? maxRefundAmount : null;
    refundForm.method = latestPaymentMethodFor(sourceType, sourceId);

    if (maxRefundAmount <= 0) {
      refundLookup.error = '此單已無可退款金額';
    }
  } catch (error) {
    resetRefundLookup();
    refundLookup.error = error.response?.data?.detail || '查詢單據失敗';
  } finally {
    refundLookup.loading = false;
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
    resetRefundLookup();
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

let refundLookupTimer = null;
watch(
  () => [refundForm.source_type, refundForm.source_id],
  () => {
    if (refundLookupTimer) clearTimeout(refundLookupTimer);
    refundLookupTimer = setTimeout(lookupRefundSource, 350);
  }
);

watch(
  () => route.query.report,
  (report) => {
    if (reportTabs.includes(report)) activeTab.value = report;
  }
);

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

.report-heading {
  align-items: flex-end;

  p {
    margin: 0.35rem 0 0;
    color: $text-secondary;
  }
}

.report-period-control {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 180px;
  color: $text-secondary;
  font-size: 0.9rem;
}

.report-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.report-summary-item {
  min-width: 0;
  padding: 0.9rem;
  border: 1px solid $medium-grey;
  border-radius: 6px;
  background: $background-color;

  span,
  strong {
    display: block;
  }

  span {
    margin-bottom: 0.35rem;
    color: $text-secondary;
    font-size: 0.82rem;
  }

  strong {
    color: $text-primary;
    font-size: 1.05rem;
  }

  &.income strong { color: #86efac; }
  &.refund strong,
  &.expense strong { color: #fca5a5; }
  &.net strong { color: $primary-light; }
}

.report-table {
  min-width: 680px;
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

.lookup-state {
  margin: -0.25rem 0 1rem;
  color: $text-secondary;
  font-size: 0.9rem;

  .error-text {
    color: #fca5a5;
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

  .report-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
