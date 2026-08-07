<template>
  <div class="admin-dashboard" :class="{ 'sidebar-open': isSidebarOpen }">
    <div class="mobile-topbar">
      <button class="hamburger-btn" @click="isSidebarOpen = !isSidebarOpen">
        <span class="bar"></span>
        <span class="bar"></span>
        <span class="bar"></span>
      </button>
      <span class="mobile-title">{{ settings.store_name }} 後台</span>
    </div>

    <div class="sidebar-overlay" @click="isSidebarOpen = false"></div>

    <aside class="sidebar">
      <h2>{{ settings.store_name }}</h2>
      <nav>
        <router-link to="/admin" exact-active-class="active" @click="closeSidebar">儀表板</router-link>
        <router-link to="/admin/bookings" active-class="active" @click="closeSidebar">預約管理</router-link>
        <router-link to="/admin/work-orders" active-class="active" @click="closeSidebar">工單管理</router-link>
        <router-link to="/admin/members" active-class="active" @click="closeSidebar">客戶 / 會員管理</router-link>
        <router-link to="/admin/products" active-class="active" @click="closeSidebar">商城管理</router-link>
        <router-link to="/admin/inventory" active-class="active" @click="closeSidebar">庫存管理</router-link>
        <router-link to="/admin/purchases" active-class="active" @click="closeSidebar">採購 / 叫貨管理</router-link>
        <router-link to="/admin/accounting" active-class="active" @click="closeSidebar">帳務管理</router-link>
        <router-link to="/admin/announcements" active-class="active" @click="closeSidebar">公告管理</router-link>
        <router-link to="/admin/portfolio" active-class="active" @click="closeSidebar">作品集管理</router-link>
        <router-link to="/admin/admins" active-class="active" @click="closeSidebar">系統與權限</router-link>
        <router-link to="/admin/settings" active-class="active" @click="closeSidebar">全域系統設定</router-link>
      </nav>
      <button @click="handleLogout" class="btn-logout">登出</button>
    </aside>

    <main class="content">
      <header>
        <h1>{{ $route.path === '/admin' ? '儀表板' : routeTitle }}</h1>
        <p v-if="$route.path === '/admin'">每日待辦提醒，管理員 {{ adminUser?.full_name || adminUser?.username }}。</p>
      </header>

      <div class="dashboard-content">
        <router-view v-slot="{ Component }" v-if="$route.path !== '/admin'">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>

        <div v-else class="overview">
          <div v-if="loading" class="loading-state">
            <div class="loader-spinner"></div>
            <p>載入儀表板資料...</p>
          </div>

          <template v-else>
            <section class="reminder-card">
              <div class="card-header">
                <div>
                  <h3>今日預約</h3>
                  <span>顯示今天仍在預約中的項目</span>
                </div>
                <div class="header-actions">
                  <strong>{{ todayBookings.length }}</strong>
                  <router-link :to="{ path: '/admin/bookings', query: { date: todayStr } }">查看全部</router-link>
                </div>
              </div>
              <table v-if="todayBookingPreview.length" class="summary-table">
                <thead>
                  <tr>
                    <th>時間</th>
                    <th>客戶</th>
                    <th>車輛</th>
                    <th>項目</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="booking in todayBookingPreview" :key="booking.id">
                    <td class="time">{{ formatTime(booking.booking_time) }}</td>
                    <td>{{ booking.user?.name || '—' }}</td>
                    <td>{{ booking.motor?.license_plate || '—' }}</td>
                    <td>{{ bookingCategoryMap[booking.category] || booking.category }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-state">今天沒有待處理預約。</div>
            </section>

            <section class="reminder-card">
              <div class="card-header">
                <div>
                  <h3>進行中工單</h3>
                  <span>尚未結案、尚未進入收款的工單</span>
                </div>
                <div class="header-actions">
                  <strong>{{ activeWorkOrders.length }}</strong>
                  <router-link :to="{ path: '/admin/work-orders', query: { status: 'active' } }">查看全部</router-link>
                </div>
              </div>
              <table v-if="activeWorkOrderPreview.length" class="summary-table">
                <thead>
                  <tr>
                    <th>工單</th>
                    <th>預約單</th>
                    <th>狀態</th>
                    <th>金額</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="workOrder in activeWorkOrderPreview" :key="workOrder.id">
                    <td>#{{ workOrder.id }}</td>
                    <td>{{ workOrder.booking_id ? `#${workOrder.booking_id}` : '現場工單' }}</td>
                    <td><span class="status-tag" :class="workOrder.status">{{ workOrderStatusMap[workOrder.status] || workOrder.status }}</span></td>
                    <td class="amount">NT$ {{ workOrder.total_amount?.toLocaleString() || 0 }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-state">目前沒有進行中工單。</div>
            </section>

            <section class="reminder-card">
              <div class="card-header">
                <div>
                  <h3>待主管確認</h3>
                  <span>退款、折扣、異常報價、工單結案與追加項目</span>
                </div>
                <div class="header-actions">
                  <strong>{{ approvalItems.length }}</strong>
                  <router-link to="/admin/approvals">查看全部</router-link>
                </div>
              </div>
              <table v-if="approvalPreview.length" class="summary-table">
                <thead>
                  <tr>
                    <th>類型</th>
                    <th>內容</th>
                    <th>來源</th>
                    <th>建立時間</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in approvalPreview" :key="item.id">
                    <td>{{ item.type }}</td>
                    <td>{{ item.title }}</td>
                    <td>{{ item.source }}</td>
                    <td>{{ formatDate(item.created_at) }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-state">目前沒有待主管確認項目。</div>
            </section>

            <section class="reminder-card">
              <div class="card-header">
                <div>
                  <h3>待到貨項目</h3>
                  <span>以已訂貨但尚未到貨的訂單商品為準</span>
                </div>
                <div class="header-actions">
                  <strong>{{ awaitingArrivalItems.length }}</strong>
                  <router-link :to="{ path: '/admin/purchases', query: { status: 'awaiting-arrival' } }">查看全部</router-link>
                </div>
              </div>
              <table v-if="awaitingArrivalPreview.length" class="summary-table">
                <thead>
                  <tr>
                    <th>項目名稱</th>
                    <th>數量</th>
                    <th>客戶 / 工單</th>
                    <th>預計到貨日</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in awaitingArrivalPreview" :key="item.id">
                    <td>{{ item.name }}</td>
                    <td>{{ item.quantity }}</td>
                    <td>{{ item.customerRef }}</td>
                    <td>{{ item.expectedArrivalDate || '未設定' }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-state">目前沒有待到貨項目。</div>
            </section>

            <section class="reminder-card">
              <div class="card-header">
                <div>
                  <h3>待付款 / 待收款</h3>
                  <span>未付款訂單、訂金尾款與工單待收款</span>
                </div>
                <div class="header-actions">
                  <strong>{{ receivableItems.length }}</strong>
                  <router-link :to="{ path: '/admin/accounting', query: { status: 'receivable' } }">查看全部</router-link>
                </div>
              </div>
              <table v-if="receivablePreview.length" class="summary-table">
                <thead>
                  <tr>
                    <th>來源</th>
                    <th>客戶 / 單號</th>
                    <th>狀態</th>
                    <th>金額</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in receivablePreview" :key="item.id">
                    <td>{{ item.source }}</td>
                    <td>{{ item.customerRef }}</td>
                    <td><span class="status-tag" :class="item.status">{{ item.statusLabel }}</span></td>
                    <td class="amount">NT$ {{ item.amount?.toLocaleString() || 0 }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-state">目前沒有待付款或待收款項目。</div>
            </section>
          </template>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useAuthStore } from '../../store/auth';
import { useSiteStore } from '../../store/site';
import { getAdminBookings, getAllOrders, getPurchaseRequests, getWorkOrderApprovals, getWorkOrders } from '../../api/admin';

const authStore = useAuthStore();
const siteStore = useSiteStore();
const router = useRouter();
const route = useRoute();
const { adminUser } = storeToRefs(authStore);
const { settings } = storeToRefs(siteStore);

const isSidebarOpen = ref(false);
const allBookings = ref([]);
const allOrders = ref([]);
const allWorkOrders = ref([]);
const purchaseRequests = ref([]);
const loading = ref(false);

const todayStr = new Date().toLocaleDateString('en-CA');
const previewLimit = 5;
const approvalItems = ref([]);
const activeBookingStatuses = ['PENDING', 'CONFIRMED', 'ARRIVED'];

const closeSidebar = () => {
  isSidebarOpen.value = false;
};

const routeTitle = computed(() => route.meta?.title || '後台管理');

const bookingCategoryMap = {
  REPAIR: '維修',
  MAINTENANCE: '保養',
  CONSULTATION: '諮詢'
};

const orderStatusMap = {
  PENDING: '未付款',
  DEPOSIT_PAID: '已付訂金',
  FULL_PAID: '已付全款',
  COMPLETED: '已結案',
  CANCELED: '已取消'
};

const orderPaymentStatusMap = {
  PENDING: '待付款',
  VERIFYING: '付款確認中',
  PAID: '已付款',
  FAILED: '付款失敗',
  PARTIALLY_REFUNDED: '部分退款',
  REFUNDED: '已退款',
  CANCELED: '已取消'
};

const approvalTypeMap = {
  DISCOUNT: '折扣',
  HIGH_QUOTE: '高額報價',
  STATUS_CHANGE: '狀態變更',
  INVENTORY_RESERVATION: '確認預留',
  INVENTORY_CONSUMPTION: '確認扣庫存'
};

const workOrderStatusMap = {
  PENDING: '待檢查',
  INSPECTION_PENDING: '待檢查',
  QUOTE_PENDING: '待報價',
  CUSTOMER_CONFIRMATION_PENDING: '等待客戶確認',
  SUPERVISOR_APPROVAL_PENDING: '待主管確認',
  IN_PROGRESS: '進行中',
  AWAITING_PAYMENT: '待收款',
  COMPLETED: '已完工',
  CANCELED: '已取消'
};

const todayBookings = computed(() => {
  return allBookings.value
    .filter(booking => booking?.booking_time?.startsWith(todayStr) && activeBookingStatuses.includes(booking.status))
    .sort((a, b) => new Date(a.booking_time) - new Date(b.booking_time));
});

const activeWorkOrders = computed(() => {
  return allWorkOrders.value
    .filter(workOrder => [
      'PENDING',
      'INSPECTION_PENDING',
      'QUOTE_PENDING',
      'CUSTOMER_CONFIRMATION_PENDING',
      'SUPERVISOR_APPROVAL_PENDING',
      'IN_PROGRESS'
    ].includes(workOrder.status))
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
});

const awaitingArrivalItems = computed(() => {
  return purchaseRequests.value.map(request => ({
    id: `purchase-${request.id}`,
    name: request.item_name || request.product?.name || `#${request.product_id}`,
    quantity: Math.max(0, (request.requested_quantity || 0) - (request.arrived_quantity || 0)),
    customerRef: `${request.customer_name || '未填客戶'} / 工單 #${request.work_order_id || '-'}`,
    expectedArrivalDate: request.expected_arrival_date || null
  })).sort((a, b) => {
    if (!a.expectedArrivalDate && !b.expectedArrivalDate) return 0;
    if (!a.expectedArrivalDate) return 1;
    if (!b.expectedArrivalDate) return -1;
    return new Date(a.expectedArrivalDate) - new Date(b.expectedArrivalDate);
  });

  const items = [];
  for (const order of allOrders.value) {
    for (const item of order.items || []) {
      if (item.status !== 'ORDERED') continue;
      items.push({
        id: `order-${order.id}-item-${item.id}`,
        name: item.product?.name || `商品 #${item.product_id}`,
        quantity: item.quantity,
        customerRef: `${order.recipient_name || '—'} / 訂單 #${order.id}`,
        expectedArrivalDate: item.expected_arrival_date || null
      });
    }
  }

  return items.sort((a, b) => {
    if (!a.expectedArrivalDate && !b.expectedArrivalDate) return 0;
    if (!a.expectedArrivalDate) return 1;
    if (!b.expectedArrivalDate) return -1;
    return new Date(a.expectedArrivalDate) - new Date(b.expectedArrivalDate);
  });
});

const receivableItems = computed(() => {
  const orderItems = allOrders.value
    .filter(order => order.source === 'online' && ['PENDING', 'VERIFYING', 'FAILED'].includes(order.payment_status))
    .map(order => ({
      id: `order-${order.id}`,
      source: order.source === 'instore' ? '現場訂單' : '線上訂單',
      customerRef: `${order.recipient_name || '—'} / #${order.id}`,
      status: order.payment_status,
      statusLabel: orderPaymentStatusMap[order.payment_status] || order.payment_status,
      amount: order.total_amount || 0,
      dueDate: null
    }));

  const workOrderItems = allWorkOrders.value
    .filter(workOrder => workOrder.status === 'AWAITING_PAYMENT' && ['UNPAID', 'PARTIALLY_PAID'].includes(workOrder.payment_status))
    .map(workOrder => ({
      id: `work-order-${workOrder.id}`,
      source: '工單',
      customerRef: `${workOrder.customer_name || '—'} / 工單 #${workOrder.id}`,
      status: workOrder.status,
      statusLabel: workOrderStatusMap[workOrder.status] || workOrder.status,
      amount: workOrder.balance_amount ?? workOrder.total_amount ?? 0,
      dueDate: null
    }));

  return [...orderItems, ...workOrderItems].sort((a, b) => {
    if (a.dueDate && b.dueDate) return new Date(a.dueDate) - new Date(b.dueDate);
    if (a.dueDate) return -1;
    if (b.dueDate) return 1;
    return b.amount - a.amount;
  });
});

const todayBookingPreview = computed(() => todayBookings.value.slice(0, previewLimit));
const activeWorkOrderPreview = computed(() => activeWorkOrders.value.slice(0, previewLimit));
const approvalPreview = computed(() => approvalItems.value.slice(0, previewLimit));
const awaitingArrivalPreview = computed(() => awaitingArrivalItems.value.slice(0, previewLimit));
const receivablePreview = computed(() => receivableItems.value.slice(0, previewLimit));

const formatTime = (iso) => {
  if (!iso) return '—';
  const date = new Date(iso);
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const formatDate = (iso) => {
  if (!iso) return '—';
  const date = new Date(iso);
  return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')}`;
};

const fetchDashboardData = async () => {
  loading.value = true;
  try {
    const [bookings, orders, workOrders, approvals, purchases] = await Promise.all([
      getAdminBookings({ skip: 0, limit: 200, date_str: todayStr }),
      getAllOrders(),
      getWorkOrders({ skip: 0, limit: 200 }),
      getWorkOrderApprovals({ status: 'PENDING' }),
      getPurchaseRequests({ status: 'awaiting-arrival', limit: 200 })
    ]);

    allBookings.value = Array.isArray(bookings) ? bookings : [];
    allOrders.value = Array.isArray(orders) ? orders : [];
    allWorkOrders.value = Array.isArray(workOrders) ? workOrders : [];
    purchaseRequests.value = Array.isArray(purchases) ? purchases : [];
    approvalItems.value = Array.isArray(approvals)
      ? approvals.map(item => ({
          id: item.id,
          type: approvalTypeMap[item.type] || item.type,
          title: item.title,
          source: `工單 #${item.work_order_id}`,
          created_at: item.requested_at
        }))
      : [];
  } catch (error) {
    console.error('載入儀表板資料失敗:', error);
  } finally {
    loading.value = false;
  }
};

const handleLogout = () => {
  authStore.adminLogout();
  router.push('/admin-login');
};

onMounted(() => {
  fetchDashboardData();
  siteStore.fetchSettings();
});
</script>

<style lang="scss" scoped>
@use '../../assets/_variables.scss' as *;

.admin-dashboard {
  display: flex;
  min-height: 100vh;
  background-color: $dark-grey;
  color: $text-primary;

  .mobile-topbar {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 56px;
    background-color: $background-color;
    border-bottom: 1px solid $medium-grey;
    align-items: center;
    padding: 0 1rem;
    gap: 1rem;
    z-index: 200;

    .hamburger-btn {
      background: none;
      border: none;
      cursor: pointer;
      padding: 4px;
      display: flex;
      flex-direction: column;
      gap: 5px;

      .bar {
        display: block;
        width: 24px;
        height: 2px;
        background-color: $text-primary;
        border-radius: 2px;
      }
    }

    .mobile-title {
      color: $primary-light;
      font-weight: bold;
      font-size: 1.1rem;
    }
  }

  .sidebar-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 299;
  }

  .sidebar {
    width: 250px;
    background-color: $background-color;
    border-right: 1px solid $medium-grey;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;

    h2 {
      padding: 1.5rem;
      color: $primary-light;
      border-bottom: 1px solid $medium-grey;
      margin: 0;
    }

    nav {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 1rem 0;

      a {
        padding: 1rem 1.5rem;
        color: $text-secondary;
        text-decoration: none;
        transition: 0.3s;

        &:hover,
        &.active {
          background-color: rgba($primary-color, 0.1);
          color: $primary-color;
          border-right: 3px solid $primary-color;
        }
      }
    }

    .btn-logout {
      padding: 1rem;
      background-color: transparent;
      color: #ff6b6b;
      border: none;
      border-top: 1px solid $medium-grey;
      cursor: pointer;
      font-weight: bold;

      &:hover {
        background-color: rgba(#ff6b6b, 0.1);
      }
    }
  }

  .content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;

    header {
      padding: 1.5rem 2.5rem;
      border-bottom: 1px solid $medium-grey;

      h1 {
        margin: 0 0 0.5rem;
        color: $primary-color;
      }

      p {
        margin: 0;
        color: $light-grey;
      }
    }
  }

  .dashboard-content {
    padding: 2rem;
  }

  .overview {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1.5rem;
  }

  .loading-state {
    grid-column: 1 / -1;
    min-height: 260px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: $text-disabled;
  }

  .loader-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(255, 255, 255, 0.1);
    border-top-color: $primary-color;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  .reminder-card {
    background-color: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    min-height: 245px;
    padding: 1.25rem;
    overflow: hidden;

    .card-header {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      align-items: flex-start;
      margin-bottom: 1rem;

      h3 {
        margin: 0 0 0.25rem;
        color: $primary-light;
        font-size: 1.05rem;
      }

      span {
        color: $text-secondary;
        font-size: 0.84rem;
      }

      .header-actions {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        white-space: nowrap;

        strong {
          color: #fff;
          background-color: $primary-color;
          min-width: 30px;
          height: 26px;
          padding: 0 0.45rem;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 999px;
          font-size: 0.85rem;
        }

        a {
          color: $primary-light;
          text-decoration: none;
          font-size: 0.85rem;
          font-weight: 600;

          &:hover {
            text-decoration: underline;
          }
        }
      }
    }
  }

  .summary-table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      padding: 0.62rem 0.45rem;
      text-align: left;
      border-bottom: 1px solid rgba($medium-grey, 0.55);
      font-size: 0.86rem;
      vertical-align: middle;
    }

    th {
      color: $text-disabled;
      font-weight: 600;
      font-size: 0.76rem;
    }

    .time,
    .amount {
      color: $primary-light;
      font-weight: 700;
    }
  }

  .status-tag {
    display: inline-flex;
    padding: 0.18rem 0.52rem;
    border-radius: 999px;
    font-size: 0.76rem;
    background-color: rgba($medium-grey, 0.35);

    &.PENDING { color: #ffc107; background-color: rgba(#ffc107, 0.14); }
    &.DEPOSIT_PAID,
    &.AWAITING_PAYMENT { color: #ff9800; background-color: rgba(#ff9800, 0.14); }
    &.IN_PROGRESS { color: #64b5f6; background-color: rgba(#64b5f6, 0.14); }
  }

  .empty-state {
    min-height: 145px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: $text-disabled;
    font-size: 0.9rem;
    text-align: center;
  }

  @media (max-width: 1024px) {
    .overview {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 768px) {
    flex-direction: column;

    .mobile-topbar {
      display: flex;
    }

    .sidebar {
      position: fixed;
      top: 0;
      left: 0;
      height: 100vh;
      width: 260px;
      z-index: 300;
      transform: translateX(-100%);
      transition: transform 0.3s ease;
    }

    &.sidebar-open {
      .sidebar {
        transform: translateX(0);
      }

      .sidebar-overlay {
        display: block;
      }
    }

    .content {
      padding-top: 56px;

      header {
        padding: 1rem;

        h1 {
          font-size: 1.25rem;
        }
      }
    }

    .dashboard-content {
      padding: 1rem;
    }

    .reminder-card {
      padding: 1rem;
      min-height: 220px;
    }

    .summary-table {
      th,
      td {
        padding: 0.5rem 0.35rem;
        font-size: 0.78rem;
      }
    }
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
