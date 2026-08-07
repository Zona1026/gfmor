<template>
  <div class="admin-approvals">
    <div class="section-header">
      <div>
        <h2>待主管確認</h2>
        <p>處理工單折扣、高額報價與狀態變更審核。</p>
      </div>
      <button class="btn btn-outline" @click="fetchApprovals">重新整理</button>
    </div>

    <div class="filter-row">
      <button
        v-for="option in filterOptions"
        :key="option.value"
        class="filter-btn"
        :class="{ active: activeStatus === option.value }"
        @click="setFilter(option.value)"
      >
        {{ option.label }}
      </button>
    </div>

    <div v-if="loading" class="empty-state">載入中...</div>
    <div v-else class="table-wrap">
      <table v-if="approvals.length" class="approval-table">
        <thead>
          <tr>
            <th>類型</th>
            <th>工單</th>
            <th>客戶 / 車牌</th>
            <th>原因</th>
            <th>狀態</th>
            <th>建立時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="approval in approvals" :key="approval.id">
            <td>{{ approvalTypeMap[approval.type] || approval.type }}</td>
            <td>#{{ approval.work_order_id }}</td>
            <td>
              <strong>{{ approval.work_order?.customer_name || '-' }}</strong>
              <span class="secondary-line">{{ approval.work_order?.vehicle_license_plate || '-' }}</span>
            </td>
            <td class="reason-cell">{{ approval.reason || approval.title }}</td>
            <td><span class="status-tag" :class="approval.status">{{ approvalStatusMap[approval.status] || approval.status }}</span></td>
            <td>{{ formatDateTime(approval.requested_at) }}</td>
            <td>
              <div v-if="approval.status === 'PENDING' && canReview" class="action-buttons">
                <button class="btn btn-primary" @click="reviewApproval(approval.id, true)">核准</button>
                <button class="btn btn-danger" @click="reviewApproval(approval.id, false)">退回</button>
              </div>
              <span v-else-if="approval.status === 'PENDING'" class="secondary-line">僅最高級可處理</span>
              <span v-else class="secondary-line">{{ approval.reviewed_by || '已處理' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">目前沒有符合條件的主管審核項目。</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { approveWorkOrderApproval, getWorkOrderApprovals, rejectWorkOrderApproval } from '../../api/admin';
import { useAuthStore } from '../../store/auth';

const loading = ref(false);
const approvals = ref([]);
const activeStatus = ref('PENDING');
const authStore = useAuthStore();
const { adminUser } = storeToRefs(authStore);
const canReview = computed(() => adminUser.value?.role === '最高級');

const filterOptions = [
  { label: '待審核', value: 'PENDING' },
  { label: '已核准', value: 'APPROVED' },
  { label: '已退回', value: 'REJECTED' },
  { label: '全部', value: '' }
];

const approvalTypeMap = {
  DISCOUNT: '折扣',
  HIGH_QUOTE: '高額報價',
  STATUS_CHANGE: '狀態變更',
  INVENTORY_RESERVATION: '確認預留',
  INVENTORY_CONSUMPTION: '確認扣庫存'
};

const approvalStatusMap = {
  PENDING: '待審核',
  APPROVED: '已核准',
  REJECTED: '已退回'
};

const setFilter = (status) => {
  activeStatus.value = status;
  fetchApprovals();
};

const fetchApprovals = async () => {
  loading.value = true;
  try {
    const params = activeStatus.value ? { status: activeStatus.value } : {};
    approvals.value = await getWorkOrderApprovals(params);
  } catch (error) {
    console.error('載入審核項目失敗:', error);
    approvals.value = [];
  } finally {
    loading.value = false;
  }
};

const reviewApproval = async (id, approved) => {
  try {
    const payload = { reviewed_by: '主管' };
    if (approved) await approveWorkOrderApproval(id, payload);
    else await rejectWorkOrderApproval(id, payload);
    await fetchApprovals();
  } catch (error) {
    alert(`審核失敗：${getErrorMessage(error)}`);
  }
};

const formatDateTime = (iso) => {
  if (!iso) return '-';
  const date = new Date(iso);
  return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const getErrorMessage = (error) => {
  const detail = error.response?.data?.detail;
  if (!detail) return '未知錯誤';
  if (typeof detail === 'string') return detail;
  return JSON.stringify(detail);
};

onMounted(fetchApprovals);
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-approvals {
  color: $text-primary;

  .section-header,
  .filter-row,
  .action-buttons {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .section-header {
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;

    h2 {
      color: $primary-light;
      margin: 0 0 0.4rem;
    }

    p {
      color: $text-secondary;
      margin: 0;
    }
  }

  .filter-row {
    margin-bottom: 1rem;
  }

  .btn,
  .filter-btn {
    padding: 0.55rem 0.9rem;
    border: 1px solid $medium-grey;
    background: rgba(255, 255, 255, 0.04);
    color: $text-secondary;
    border-radius: $border-radius;
    cursor: pointer;
    font-weight: 700;

    &.active,
    &:hover {
      border-color: $primary-color;
      color: $primary-light;
      background: rgba($primary-color, 0.1);
    }
  }

  .btn-primary {
    background: $primary-color;
    border-color: $primary-color;
    color: #fff;
  }

  .btn-danger {
    border-color: #e57373;
    color: #e57373;
  }

  .btn-outline {
    color: $primary-light;
  }

  .table-wrap {
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    background-color: $dark-grey;
    overflow: auto;
  }

  .approval-table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      padding: 0.85rem 1rem;
      border-bottom: 1px solid $medium-grey;
      text-align: left;
      white-space: nowrap;
      vertical-align: top;
    }

    th {
      background: $background-color;
      color: $text-secondary;
      font-size: 0.88rem;
    }
  }

  .reason-cell {
    max-width: 320px;
    white-space: normal;
  }

  .secondary-line {
    display: block;
    color: $text-secondary;
    font-size: 0.82rem;
    margin-top: 0.22rem;
  }

  .status-tag {
    display: inline-flex;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.8rem;

    &.PENDING { color: #ffb74d; background-color: rgba(#ffb74d, 0.15); }
    &.APPROVED { color: #81c784; background-color: rgba(#81c784, 0.15); }
    &.REJECTED { color: #e57373; background-color: rgba(#e57373, 0.15); }
  }

  .empty-state {
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    background-color: $dark-grey;
    color: $text-disabled;
    padding: 3rem;
    text-align: center;
  }
}
</style>
