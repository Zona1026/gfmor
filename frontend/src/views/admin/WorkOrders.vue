<template>
  <div class="admin-work-orders">
    <div class="section-header">
      <div>
        <h2>工單管理</h2>
        <p>以車牌快速找單，並管理報價、施工、收款與主管審核。</p>
      </div>
      <button v-if="canCreateWorkOrder" class="btn btn-primary" @click="openCreateModal">新增工單</button>
    </div>

    <div class="filter-bar">
      <label class="filter-control">
        <span>依工單類型篩選</span>
        <select v-model="serviceTypeFilter" @change="applyFilters">
          <option value="">全部類型</option>
          <option v-for="option in serviceTypeFilterOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>
      <label class="filter-control">
        <span>依工單狀態篩選</span>
        <select v-model="statusSelectFilter" @change="applyFilters">
          <option value="">全部狀態</option>
          <option v-for="option in statusFilterOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>
      <button
        type="button"
        class="btn btn-outline supervisor-filter-btn"
        :class="{ active: statusFilter === 'SUPERVISOR_APPROVAL_PENDING' }"
        @click="showSupervisorPendingWorkOrders"
      >
        待主管確認
      </button>
    </div>

    <div class="toolbar">
      <div class="search-box">
        <input
          v-model.trim="searchKeyword"
          type="search"
          placeholder="搜尋車牌、客戶、電話、預約單號或工單號"
          @keyup.enter="applyFilters"
        />
        <button class="btn btn-primary" @click="applyFilters">搜尋</button>
      </div>
      <input v-model="filterDate" type="date" class="date-picker" @change="applyFilters" />
      <button class="btn btn-outline" @click="showTodayWorkOrders">今日工單</button>
      <button class="btn btn-ghost" @click="clearFilters">清除</button>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <div v-else class="table-wrap">
      <table v-if="workOrders.length" class="work-order-table">
        <thead>
          <tr>
            <th>工單</th>
            <th>客戶</th>
            <th>車輛 / 設備</th>
            <th>服務類型</th>
            <th>工單狀態</th>
            <th>付款狀態</th>
            <th>負責人</th>
            <th>預約時間</th>
            <th>消費日期</th>
            <th>總金額</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="workOrder in workOrders" :key="workOrder.id" @click="openDetail(workOrder.id)">
            <td class="strong-cell">#{{ workOrder.id }}</td>
            <td>
              <strong>{{ workOrder.customer_name || workOrder.booking?.user?.name || '-' }}</strong>
              <span class="secondary-line">{{ workOrder.customer_phone || workOrder.booking?.user?.phone || '-' }}</span>
            </td>
            <td class="strong-cell">
              {{ workOrder.vehicle_license_plate || workOrder.booking?.motor?.license_plate || '-' }}
              <span class="secondary-line">{{ workOrder.vehicle_model || workOrder.booking?.motor?.model_name || '-' }}</span>
            </td>
            <td>{{ serviceTypeMap[workOrder.service_type] || workOrder.service_type }}</td>
            <td>
              <span class="status-tag" :class="workOrder.status">
                {{ statusMap[workOrder.status] || workOrder.status }}
              </span>
            </td>
            <td>
              <span class="payment-tag" :class="workOrder.payment_status">
                {{ paymentStatusMap[workOrder.payment_status] || workOrder.payment_status }}
              </span>
            </td>
            <td>{{ workOrder.responsible_staff || '-' }}</td>
            <td>{{ formatDateTime(workOrder.scheduled_at || workOrder.booking?.booking_time) }}</td>
            <td>{{ formatDate(workOrder.consumption_date) }}</td>
            <td class="amount">NT$ {{ workOrder.total_amount?.toLocaleString() || 0 }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">目前沒有符合條件的工單。</div>
    </div>

    <div v-if="showCreateModal && canCreateWorkOrder" class="modal-overlay" @click.self="closeCreateModal">
      <div class="modal-content large">
        <div class="modal-header">
          <h3>新增工單</h3>
          <button class="icon-btn" @click="closeCreateModal">×</button>
        </div>

        <form class="work-order-form" @submit.prevent="submitCreateWorkOrder">
          <section class="form-section">
            <h4>客戶來源</h4>
            <div class="segmented">
              <button type="button" :class="{ active: createSource === 'member' }" @click="createSource = 'member'">會員</button>
              <button type="button" :class="{ active: createSource === 'guest' }" @click="createSource = 'guest'">散客</button>
            </div>

            <div v-if="createSource === 'member'" class="source-grid">
              <div class="form-row search-row">
                <input v-model.trim="memberSearch" placeholder="輸入會員姓名、電話或車牌搜尋" @keydown.enter.prevent="handleMemberSearch" />
                <button type="button" class="btn btn-outline" @click="handleMemberSearch">搜尋會員</button>
              </div>
              <label>
                會員車輛
                <select v-model="selectedMemberMotorKey" @change="applySelectedMemberMotor">
                  <option value="">請選擇會員車輛</option>
                  <option v-for="option in memberMotorOptions" :key="option.key" :value="option.key">
                    {{ option.user.name }} / {{ option.motor.license_plate }} / {{ option.motor.model_name || '未填車型' }}
                  </option>
                </select>
              </label>
            </div>

            <div v-else class="source-grid">
              <div class="form-row search-row">
                <input v-model.trim="guestSearch" placeholder="輸入散客姓名、電話或車牌搜尋" @keydown.enter.prevent="handleGuestSearch" />
                <button type="button" class="btn btn-outline" @click="handleGuestSearch">搜尋散客</button>
              </div>
              <div v-if="guestResults.length" class="result-list">
                <button
                  v-for="option in guestMotorOptions"
                  :key="option.key"
                  type="button"
                  @click="selectGuestMotor(option)"
                >
                  {{ option.guest.name }} / {{ option.guest.phone }}
                  <template v-if="option.motor">
                    / {{ option.motor.license_plate }} / {{ option.motor.model_name || '未填車型' }}
                  </template>
                </button>
              </div>
              <div class="form-grid">
                <label>
                  <span class="field-label">散客姓名 <span class="required-mark">*</span></span>
                  <input v-model.trim="createForm.guest_name" required />
                </label>
                <label>
                  <span class="field-label">散客電話 <span class="required-mark">*</span></span>
                  <input v-model.trim="createForm.guest_phone" required />
                </label>
              </div>
            </div>
          </section>

          <section class="form-section">
            <h4>基本資料</h4>
            <div class="form-grid">
              <label>
                <span class="field-label">車牌 <span class="required-mark">*</span></span>
                <input v-model.trim="createForm.vehicle_license_plate" required />
              </label>
              <label>
                品牌
                <input v-model.trim="createForm.vehicle_brand" />
              </label>
              <label>
                <span class="field-label">車型 <span class="required-mark">*</span></span>
                <input v-model.trim="createForm.vehicle_model" required />
              </label>
              <label>
                <span class="field-label">里程 <span class="required-mark">*</span></span>
                <input v-model.number="createForm.vehicle_mileage" type="number" min="0" required />
              </label>
              <label>
                服務類型
                <select v-model="createForm.service_type">
                  <option v-for="(label, value) in serviceTypeMap" :key="value" :value="value">{{ label }}</option>
                </select>
              </label>
              <label>
                <span class="field-label">負責人 <span class="required-mark">*</span></span>
                <select v-model="createForm.responsible_staff" required>
                  <option value="" disabled>請選擇負責人</option>
                  <option v-for="staff in responsibleStaffOptions" :key="staff" :value="staff">
                    {{ staff }}
                  </option>
                </select>
              </label>
              <label>
                預約時間
                <input v-model="createForm.scheduled_at" type="datetime-local" />
              </label>
              <label>
                消費日期
                <input v-model="createForm.consumption_date" type="date" required />
              </label>
              <label v-if="createSource === 'guest'" class="new-vehicle-field">
                新車
                <span><input v-model="createForm.vehicle_is_new" type="checkbox" /> 建立新車保養里程表</span>
              </label>
              <label v-if="createSource === 'guest' && createForm.vehicle_is_new">
                購車日期
                <input v-model="createForm.vehicle_purchase_date" type="date" />
              </label>
            </div>
            <label>
              問題描述
              <textarea v-model.trim="createForm.problem_description" rows="3"></textarea>
            </label>
            <label>
              備註
              <textarea v-model.trim="createForm.notes" rows="2"></textarea>
            </label>
          </section>

          <section class="form-section">
            <div class="section-title-row">
              <h4>工單明細</h4>
              <button type="button" class="btn btn-outline" @click="addCreateLineItem">新增明細</button>
            </div>
            <div class="line-editor">
              <div v-for="(item, index) in createLineItems" :key="index" class="line-row">
                <label class="line-field line-type">
                  <span>類型</span>
                  <select v-model="item.type" @change="handleLineTypeChange(item)">
                    <option v-for="(label, value) in lineItemTypeMap" :key="value" :value="value">{{ label }}</option>
                  </select>
                </label>
                <label class="line-field line-product">
                  <span>商品</span>
                  <select v-if="item.type === 'PART'" v-model.number="item.product_id" @change="applyProductToLine(item)">
                    <option :value="null">不綁商品 / 不扣庫存</option>
                    <option v-for="product in products" :key="product.id" :value="product.id">
                      {{ product.name }}
                    </option>
                  </select>
                  <input v-else value="不適用" disabled />
                </label>
                <label class="line-field line-name">
                  <span>明細名稱</span>
                  <input v-model.trim="item.name" placeholder="明細名稱" required />
                </label>
                <label class="line-field line-quantity">
                  <span>數量</span>
                  <input v-model.number="item.quantity" type="number" min="1" step="1" required />
                </label>
                <label class="line-field line-price">
                  <span>單價</span>
                  <input v-model.number="item.unit_price" type="number" min="0" />
                </label>
                <label class="membership-toggle">
                  <input v-model="item.counts_toward_membership" type="checkbox" />
                  <span>列入會員累積</span>
                </label>
                <div class="line-total">
                  <span>小計</span>
                  <strong>NT$ {{ lineItemTotal(item).toLocaleString() }}</strong>
                </div>
                <button type="button" class="icon-btn danger" @click="removeCreateLineItem(index)">×</button>
              </div>
            </div>
            <div class="total-row">
              <span>總金額</span>
              <strong>NT$ {{ createTotal.toLocaleString() }}</strong>
            </div>
            <div class="total-row membership-total">
              <span>可列入會員累積</span>
              <strong>NT$ {{ createMembershipTotal.toLocaleString() }}</strong>
            </div>
          </section>

          <div class="form-actions">
            <button type="button" class="btn btn-outline" @click="closeCreateModal">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">建立工單</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="selectedWorkOrder" class="modal-overlay" @click.self="closeDetail">
      <div class="modal-content xlarge">
        <div class="modal-header">
          <div>
            <h3>工單 #{{ selectedWorkOrder.id }}</h3>
            <p>{{ selectedWorkOrder.customer_name }} / {{ selectedWorkOrder.vehicle_license_plate }}</p>
          </div>
          <div class="modal-actions">
            <button
              v-if="canUseCriticalWorkOrder && !selectedWorkOrder.deleted_at"
              class="btn btn-danger"
              type="button"
              @click="openDeleteModal"
            >
              刪除工單
            </button>
            <button class="icon-btn" @click="closeDetail">×</button>
          </div>
        </div>

        <div class="detail-grid">
          <section class="form-section">
            <h4>基本資料</h4>
            <div class="form-grid">
              <label>
                服務類型
                <select v-model="detailForm.service_type" :disabled="!canEditWorkOrder">
                  <option v-for="(label, value) in serviceTypeMap" :key="value" :value="value">{{ label }}</option>
                </select>
              </label>
              <label>
                工單狀態
                <select v-model="detailForm.status" :disabled="!canEditWorkOrder">
                  <option
                    v-for="(label, value) in statusMap"
                    :key="value"
                    :value="value"
                    :disabled="isGatedStatus(value) && hasBlockingApproval(selectedWorkOrder, value)"
                  >
                    {{ label }}
                  </option>
                </select>
              </label>
              <label>
                負責人
                <select v-model="detailForm.responsible_staff" :disabled="!canEditWorkOrder">
                  <option v-for="staff in responsibleStaffOptions" :key="staff" :value="staff">
                    {{ staff }}
                  </option>
                </select>
              </label>
              <label>
                預約時間
                <input v-model="detailForm.scheduled_at" type="datetime-local" :disabled="!canEditWorkOrder" />
              </label>
              <label>
                消費日期
                <input v-model="detailForm.consumption_date" type="date" required :disabled="!canEditWorkOrder" />
              </label>
            </div>
            <label>
              問題描述
              <textarea v-model.trim="detailForm.problem_description" rows="3" :readonly="!canEditWorkOrder"></textarea>
            </label>
            <label>
              檢查結果
              <textarea v-model.trim="detailForm.inspection_result" rows="3" :readonly="!canEditWorkOrder"></textarea>
            </label>
            <label>
              備註
              <textarea v-model.trim="detailForm.notes" rows="2" :readonly="!canEditWorkOrder"></textarea>
            </label>
            <div v-if="hasBlockingApproval(selectedWorkOrder)" class="warning-text">
              此工單仍有待主管審核或退回項目，不能進入施工中、待收款或已完工。
            </div>
          </section>

          <section class="form-section">
            <h4>金額與付款</h4>
            <dl class="money-summary">
              <div><dt>總金額</dt><dd>NT$ {{ selectedWorkOrder.total_amount?.toLocaleString() || 0 }}</dd></div>
              <div><dt>已收款</dt><dd>NT$ {{ selectedWorkOrder.paid_amount?.toLocaleString() || 0 }}</dd></div>
              <div><dt>待收款</dt><dd>NT$ {{ selectedWorkOrder.balance_amount?.toLocaleString() || 0 }}</dd></div>
              <div><dt>付款狀態</dt><dd>{{ paymentStatusMap[selectedWorkOrder.payment_status] }}</dd></div>
              <div><dt>可列入會員累積</dt><dd>NT$ {{ selectedWorkOrder.membership_eligible_amount?.toLocaleString() || 0 }}</dd></div>
              <div><dt>已計入會員累積</dt><dd>NT$ {{ selectedWorkOrder.membership_consumption_amount?.toLocaleString() || 0 }}</dd></div>
            </dl>
            <div v-if="canManageWorkOrderPayments" class="payment-form">
              <input v-model.number="paymentForm.amount" type="number" min="1" placeholder="付款金額" />
              <select v-model="paymentForm.method">
                <option value="" disabled>付款方式</option>
                <option v-for="method in paymentMethodOptions" :key="method" :value="method">{{ method }}</option>
              </select>
              <button class="btn btn-outline" @click="submitPayment">登錄付款</button>
            </div>
            <table v-if="selectedWorkOrder.payments?.length" class="mini-table">
              <thead>
                <tr><th>時間</th><th>方式</th><th>金額</th></tr>
              </thead>
              <tbody>
                <tr v-for="payment in selectedWorkOrder.payments" :key="payment.id">
                  <td>{{ formatTaipeiDateTime(payment.paid_at) }}</td>
                  <td>{{ payment.method || '-' }}</td>
                  <td>NT$ {{ payment.amount?.toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
          </section>
        </div>

        <section class="form-section">
          <div class="section-title-row">
            <h4>施工 / 零件 / 工資 / 折扣明細</h4>
            <button v-if="canEditWorkOrder" type="button" class="btn btn-outline" :disabled="lineItemEditingLocked" @click="addDetailLineItem">新增明細</button>
          </div>
          <div class="line-editor">
            <div v-for="(item, index) in detailLineItems" :key="item.id || index" class="line-row">
              <label class="line-field line-type">
                <span>類型</span>
                <select v-model="item.type" :disabled="!canEditWorkOrder || lineItemEditingLocked || isLineItemInventoryLocked(item)">
                  <option v-for="(label, value) in lineItemTypeMap" :key="value" :value="value">{{ label }}</option>
                </select>
              </label>
              <label class="line-field line-product">
                <span>商品</span>
                <select v-if="item.type === 'PART'" v-model.number="item.product_id" :disabled="!canEditWorkOrder || lineItemEditingLocked || isLineItemInventoryLocked(item)" @change="applyProductToLine(item)">
                  <option :value="null">不綁商品 / 不扣庫存</option>
                  <option v-for="product in products" :key="product.id" :value="product.id">
                    {{ product.name }}
                  </option>
                </select>
                <input v-else value="不適用" disabled />
              </label>
              <label class="line-field line-name">
                <span>明細名稱</span>
                <input v-model.trim="item.name" :disabled="!canEditWorkOrder || lineItemEditingLocked || isLineItemInventoryLocked(item)" placeholder="明細名稱" required />
              </label>
              <label class="line-field line-quantity">
                <span>數量</span>
                <input v-model.number="item.quantity" type="number" min="1" step="1" required :disabled="!canEditWorkOrder || lineItemEditingLocked || isLineItemInventoryLocked(item)" />
              </label>
              <label class="line-field line-price">
                <span>單價</span>
                <input v-model.number="item.unit_price" type="number" min="0" :disabled="!canEditWorkOrder || lineItemEditingLocked || isLineItemInventoryLocked(item)" />
              </label>
              <label class="membership-toggle">
                <input
                  v-model="item.counts_toward_membership"
                  type="checkbox"
                  :disabled="!canEditWorkOrder || membershipSelectionLocked"
                />
                <span>列入會員累積</span>
              </label>
              <div class="line-total">
                <span>小計</span>
                <strong>NT$ {{ lineItemTotal(item).toLocaleString() }}</strong>
                <small v-if="item.type === 'PART'">{{ inventoryStatusText(item) }}</small>
              </div>
              <button v-if="canEditWorkOrder" type="button" class="icon-btn danger" :disabled="lineItemEditingLocked || isLineItemInventoryLocked(item)" @click="removeDetailLineItem(index)">×</button>
            </div>
          </div>
          <div class="total-row">
            <span>總金額</span>
            <strong>NT$ {{ detailTotal.toLocaleString() }}</strong>
          </div>
          <div class="total-row membership-total">
            <span>可列入會員累積</span>
            <strong>NT$ {{ detailMembershipTotal.toLocaleString() }}</strong>
          </div>
          <div v-if="supervisorReviewLocked" class="muted-line">主管已審核，工單明細與會員累積資格已鎖定。</div>
          <div v-else-if="hasPaymentRecord" class="muted-line">已有付款紀錄，明細內容已鎖定；會員累積資格可在主管審核前調整。</div>
          <div v-if="canEditWorkOrder" class="form-actions">
            <button class="btn btn-primary" @click="saveWorkOrder" :disabled="saving">儲存工單</button>
          </div>
        </section>

        <section class="form-section">
          <div class="section-title-row line-status-heading">
            <h4>明細狀態</h4>
            <button
              v-if="canReviewApprovals && !supervisorReviewLocked"
              type="button"
              class="btn btn-primary"
              :disabled="reviewingWorkOrder"
              @click="confirmSupervisorReview"
            >
              {{ reviewingWorkOrder ? '審核中...' : '確認審核' }}
            </button>
            <span v-else-if="supervisorReviewLocked" class="reviewed-label">
              已審核
            </span>
          </div>
          <div v-if="selectedWorkOrder.line_items?.length" class="line-status-table-wrap">
            <table class="mini-table line-status-table">
              <thead>
                <tr><th>類型</th><th>名稱</th><th>狀態</th><th>最後更新時間</th></tr>
              </thead>
              <tbody>
                <tr v-for="item in selectedWorkOrder.line_items" :key="item.id">
                  <td>{{ lineItemTypeMap[item.type] || item.type }}</td>
                  <td>{{ item.name }}</td>
                  <td>
                    <select
                      :value="item.fulfillment_status || ''"
                      :disabled="!canReviewApprovals || updatingFulfillmentItemId === item.id"
                      @change="updateLineItemFulfillment(item, $event.target.value)"
                    >
                      <option value="" disabled>請選擇</option>
                      <option v-for="(label, value) in fulfillmentStatusMap" :key="value" :value="value">
                        {{ label }}
                      </option>
                    </select>
                  </td>
                  <td>{{ formatDateTime(item.fulfillment_status_updated_at || item.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="muted-line">目前沒有工單明細。</div>
          <div v-if="!canReviewApprovals && selectedWorkOrder.line_items?.length" class="muted-line">
            僅最高級管理員可更新明細狀態。
          </div>
        </section>
      </div>
    </div>

    <div v-if="showDeleteModal" class="modal-overlay confirm-overlay" @click.self="closeDeleteModal">
      <div class="modal-content confirm-modal">
        <div class="modal-header">
          <div>
            <h3>刪除工單 #{{ selectedWorkOrder?.id }}</h3>
            <p>此動作會保留歷史紀錄，並將工單標記為已取消。</p>
          </div>
          <button class="icon-btn" type="button" @click="closeDeleteModal">×</button>
        </div>

        <label>
          刪除原因
          <textarea v-model.trim="deleteForm.reason" rows="4" placeholder="請輸入刪除原因"></textarea>
        </label>

        <div class="form-actions modal-footer-actions">
          <button type="button" class="btn btn-outline" @click="closeDeleteModal">取消</button>
          <button
            type="button"
            class="btn btn-danger"
            :disabled="saving || !deleteForm.reason"
            @click="confirmDeleteSelectedWorkOrder"
          >
            確認刪除
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useRoute, useRouter } from 'vue-router';
import {
  addWorkOrderPayment,
  confirmWorkOrderReview,
  createWorkOrder,
  deleteWorkOrder,
  getGuestCustomers,
  getProducts,
  getStaffAdmins,
  getWorkOrder,
  getWorkOrders,
  searchUsersByName,
  updateWorkOrder,
  updateWorkOrderLineItemFulfillmentStatus
} from '../../api/admin';
import { useAuthStore } from '../../store/auth';
import { formatTaipeiDateTime } from '../../utils/dateTime';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const { adminUser } = storeToRefs(authStore);

const loading = ref(false);
const saving = ref(false);
const workOrders = ref([]);
const products = ref([]);
const staffAdmins = ref([]);
const serviceTypeFilter = ref('');
const statusFilter = ref('');
const searchKeyword = ref('');
const filterDate = ref('');
const workOrderEditorRoles = ['最高級', '管理層', '一般'];
const workOrderManagerRoles = ['最高級', '管理層'];
const defaultResponsibleStaff = '火腿';
const paymentMethodOptions = ['現金', '轉帳', 'Linepay'];
const canCreateWorkOrder = computed(() => ['最高級', '管理層', '一般'].includes(adminUser.value?.role));
const canEditWorkOrder = computed(() => workOrderEditorRoles.includes(adminUser.value?.role));
const canManageWorkOrderPayments = computed(() => workOrderManagerRoles.includes(adminUser.value?.role));
const canUseCriticalWorkOrder = computed(() => workOrderManagerRoles.includes(adminUser.value?.role));
const canReviewApprovals = computed(() => adminUser.value?.role === '最高級');

const showCreateModal = ref(false);
const createSource = ref('guest');
const memberSearch = ref('');
const memberResults = ref([]);
const selectedMemberMotorKey = ref('');
const guestSearch = ref('');
const guestResults = ref([]);
const createForm = ref(defaultCreateForm());
const createLineItems = ref([defaultLineItem()]);

const selectedWorkOrder = ref(null);
const detailForm = ref({});
const detailLineItems = ref([]);
const paymentForm = ref({ amount: null, method: '', note: '' });
const showDeleteModal = ref(false);
const deleteForm = ref({ reason: '' });
const updatingFulfillmentItemId = ref(null);
const reviewingWorkOrder = ref(false);

const serviceTypeMap = {
  REPAIR: '維修',
  MAINTENANCE: '保養',
  MODIFICATION: '改裝'
};

const statusMap = {
  INSPECTION_PENDING: '待檢查',
  QUOTE_PENDING: '待報價',
  CUSTOMER_CONFIRMATION_PENDING: '等待客戶確認',
  SUPERVISOR_APPROVAL_PENDING: '待主管確認',
  IN_PROGRESS: '施工中',
  AWAITING_PAYMENT: '待收款',
  COMPLETED: '已完工',
  CANCELED: '已取消'
};

const paymentStatusMap = {
  UNPAID: '未付款',
  PARTIALLY_PAID: '部分付款',
  PAID: '已付款',
  REFUNDED: '已退款'
};

const lineItemTypeMap = {
  SERVICE: '施工項目',
  PART: '零件 / 耗材',
  LABOR: '工資 / 服務費',
  DISCOUNT: '折扣'
};

const fulfillmentStatusMap = {
  RESERVED: '已預留',
  ORDERED: '已叫貨',
  ARRIVED: '已到貨'
};

const serviceTypeFilterOptions = [
  { label: '維修工單', value: 'REPAIR' },
  { label: '保養工單', value: 'MAINTENANCE' },
  { label: '改裝工單', value: 'MODIFICATION' }
];

const statusFilterOptions = [
  { label: '待檢查', value: 'INSPECTION_PENDING' },
  { label: '施工中', value: 'IN_PROGRESS' },
  { label: '待收款', value: 'AWAITING_PAYMENT' },
  { label: '已完工', value: 'COMPLETED' }
];

const selectableStatusFilterValues = new Set(statusFilterOptions.map(option => option.value));
const statusSelectFilter = computed({
  get: () => selectableStatusFilterValues.has(statusFilter.value) ? statusFilter.value : '',
  set: value => {
    statusFilter.value = value;
  }
});

const gatedStatuses = ['IN_PROGRESS', 'AWAITING_PAYMENT', 'COMPLETED'];

const memberMotorOptions = computed(() => {
  const options = [];
  for (const user of memberResults.value) {
    for (const motor of user.motors || []) {
      options.push({
        key: `${user.google_id}::${motor.id}`,
        user,
        motor
      });
    }
  }
  return options;
});

const normalizedSearchValue = value => (value || '').replace(/[\s-]/g, '').toLocaleLowerCase();

const guestMotorOptions = computed(() => {
  const options = [];
  for (const guest of guestResults.value) {
    const motors = (guest.motors || []).filter(motor => !motor.status);
    if (!motors.length) {
      options.push({ key: `${guest.id}::none`, guest, motor: null });
      continue;
    }
    for (const motor of motors) {
      options.push({ key: `${guest.id}::${motor.id}`, guest, motor });
    }
  }
  return options;
});

const createTotal = computed(() => calculateTotal(createLineItems.value));
const detailTotal = computed(() => calculateTotal(detailLineItems.value));
const createMembershipTotal = computed(() => calculateMembershipTotal(createLineItems.value));
const detailMembershipTotal = computed(() => calculateMembershipTotal(detailLineItems.value));
const supervisorReviewLocked = computed(() => Boolean(selectedWorkOrder.value?.supervisor_reviewed_at));
const hasPaymentRecord = computed(() => Number(selectedWorkOrder.value?.paid_amount || 0) > 0);
const lineItemEditingLocked = computed(() => hasPaymentRecord.value || supervisorReviewLocked.value);
const membershipSelectionLocked = computed(() => supervisorReviewLocked.value);
const responsibleStaffOptions = computed(() => {
  const names = staffAdmins.value
    .map(admin => admin.full_name || admin.username)
    .filter(Boolean);
  if (!names.includes(defaultResponsibleStaff)) names.unshift(defaultResponsibleStaff);
  return names;
});

function defaultCreateForm() {
  return {
    google_id: '',
    guest_customer_id: null,
    guest_motor_id: null,
    guest_name: '',
    guest_phone: '',
    motor_id: null,
    vehicle_license_plate: '',
    vehicle_brand: '',
    vehicle_model: '',
    vehicle_vin: '',
    vehicle_mileage: null,
    vehicle_is_new: false,
    vehicle_purchase_date: '',
    service_type: 'MAINTENANCE',
    problem_description: '',
    responsible_staff: defaultResponsibleStaff,
    scheduled_at: '',
    consumption_date: todayDateString(),
    notes: ''
  };
}

function defaultLineItem() {
  return {
    type: 'SERVICE',
    name: '',
    description: '',
    product_id: null,
    quantity: 1,
    unit_price: 0,
    is_confirmed: 1,
    counts_toward_membership: false
  };
}

const readQuery = () => {
  searchKeyword.value = typeof route.query.q === 'string' ? route.query.q : '';
  filterDate.value = typeof route.query.date === 'string' ? route.query.date : '';
  serviceTypeFilter.value = typeof route.query.service_type === 'string' ? route.query.service_type : '';
  statusFilter.value = typeof route.query.status === 'string' ? route.query.status : '';

  const legacyView = typeof route.query.view === 'string' ? route.query.view : '';
  if (!serviceTypeFilter.value && legacyView.startsWith('service:')) {
    serviceTypeFilter.value = legacyView.split(':')[1];
  }
  if (!statusFilter.value && legacyView.startsWith('status:')) {
    statusFilter.value = legacyView.split(':')[1];
  }
};

const buildQuery = () => {
  const query = {};
  if (serviceTypeFilter.value) query.service_type = serviceTypeFilter.value;
  if (statusFilter.value) query.status = statusFilter.value;
  if (searchKeyword.value) query.q = searchKeyword.value;
  if (filterDate.value) query.date = filterDate.value;
  return query;
};

const filterToParams = () => {
  const params = { skip: 0, limit: 200 };
  if (serviceTypeFilter.value) params.service_type = serviceTypeFilter.value;
  if (statusFilter.value) params.status = statusFilter.value;
  if (searchKeyword.value) params.q = searchKeyword.value;
  if (filterDate.value) params.date_str = filterDate.value;
  return params;
};

const applyFilters = async () => {
  await router.replace({ path: route.path, query: buildQuery() });
  await fetchWorkOrders();
};

const showSupervisorPendingWorkOrders = () => {
  statusFilter.value = statusFilter.value === 'SUPERVISOR_APPROVAL_PENDING'
    ? ''
    : 'SUPERVISOR_APPROVAL_PENDING';
  applyFilters();
};

const showTodayWorkOrders = () => {
  filterDate.value = new Date().toLocaleDateString('en-CA');
  applyFilters();
};

const clearFilters = () => {
  serviceTypeFilter.value = '';
  statusFilter.value = '';
  searchKeyword.value = '';
  filterDate.value = '';
  applyFilters();
};

const fetchWorkOrders = async () => {
  loading.value = true;
  try {
    workOrders.value = await getWorkOrders(filterToParams());
  } catch (error) {
    console.error('載入工單失敗:', error);
    workOrders.value = [];
  } finally {
    loading.value = false;
  }
};

const fetchProducts = async () => {
  try {
    products.value = await getProducts();
  } catch (error) {
    console.error('載入商品失敗:', error);
  }
};

const fetchStaffAdmins = async () => {
  try {
    staffAdmins.value = await getStaffAdmins();
  } catch (error) {
    console.error('載入負責人清單失敗:', error);
    staffAdmins.value = [];
  }
};

const openCreateModal = () => {
  showCreateModal.value = true;
  fetchProducts();
  fetchStaffAdmins();
};

const closeCreateModal = () => {
  showCreateModal.value = false;
  createSource.value = 'guest';
  createForm.value = defaultCreateForm();
  createLineItems.value = [defaultLineItem()];
  selectedMemberMotorKey.value = '';
  memberResults.value = [];
  guestResults.value = [];
};

const handleMemberSearch = async () => {
  if (!memberSearch.value) return;
  memberResults.value = await searchUsersByName(memberSearch.value);
  if (memberResults.value.length === 0) {
    selectedMemberMotorKey.value = '';
    alert('找不到符合條件的會員。');
    return;
  }

  const keyword = normalizedSearchValue(memberSearch.value);
  const firstOption = memberMotorOptions.value.find(option =>
    normalizedSearchValue(option.motor.license_plate).includes(keyword)
  ) || memberMotorOptions.value[0];
  if (!firstOption) {
    selectedMemberMotorKey.value = '';
    alert('找不到可選擇的會員車輛。');
    return;
  }

  selectedMemberMotorKey.value = firstOption.key;
  applySelectedMemberMotor();
};

const handleGuestSearch = async () => {
  if (!guestSearch.value) return;
  guestResults.value = await getGuestCustomers(guestSearch.value);
  if (guestResults.value.length === 0) {
    alert('找不到符合條件的散客。');
    return;
  }

  const keyword = normalizedSearchValue(guestSearch.value);
  const firstOption = guestMotorOptions.value.find(option =>
    normalizedSearchValue(option.motor?.license_plate).includes(keyword)
  ) || guestMotorOptions.value[0];
  if (firstOption) selectGuestMotor(firstOption);
};

const selectGuestMotor = ({ guest, motor }) => {
  createForm.value.google_id = '';
  createForm.value.motor_id = null;
  createForm.value.guest_customer_id = guest.id;
  createForm.value.guest_motor_id = motor?.id || null;
  createForm.value.guest_name = guest.name;
  createForm.value.guest_phone = guest.phone;
  if (!motor) return;
  createForm.value.vehicle_license_plate = motor.license_plate || '';
  createForm.value.vehicle_brand = motor.brand || '';
  createForm.value.vehicle_model = motor.model_name || '';
  createForm.value.vehicle_vin = motor.vin || '';
  createForm.value.vehicle_mileage = motor.mileage ?? null;
  createForm.value.vehicle_is_new = Boolean(motor.is_new_vehicle);
  createForm.value.vehicle_purchase_date = motor.purchase_date || '';
};

const applySelectedMemberMotor = () => {
  const selected = memberMotorOptions.value.find(option => option.key === selectedMemberMotorKey.value);
  if (!selected) return;
  createForm.value.guest_customer_id = null;
  createForm.value.guest_motor_id = null;
  createForm.value.guest_name = '';
  createForm.value.guest_phone = '';
  createForm.value.google_id = selected.user.google_id;
  createForm.value.motor_id = selected.motor.id;
  createForm.value.vehicle_license_plate = selected.motor.license_plate || '';
  createForm.value.vehicle_brand = selected.motor.brand || '';
  createForm.value.vehicle_model = selected.motor.model_name || '';
  createForm.value.vehicle_vin = selected.motor.vin || '';
  createForm.value.vehicle_mileage = selected.motor.mileage ?? null;
};

const addCreateLineItem = () => {
  createLineItems.value.push(defaultLineItem());
};

const removeCreateLineItem = (index) => {
  createLineItems.value.splice(index, 1);
};

const addDetailLineItem = () => {
  detailLineItems.value.push(defaultLineItem());
};

const removeDetailLineItem = (index) => {
  detailLineItems.value.splice(index, 1);
};

const handleLineTypeChange = (item) => {
  if (item.type !== 'PART') item.product_id = null;
};

const applyProductToLine = (item) => {
  const product = products.value.find(product => product.id === Number(item.product_id));
  if (!product) return;
  item.name = product.name;
  item.unit_price = product.price;
};

const lineItemTotal = (item) => {
  return Math.max(0, Number(item.quantity) || 0) * Math.max(0, Number(item.unit_price) || 0);
};

const isLineItemInventoryLocked = (item) => {
  return Boolean(item.inventory_deducted)
    || Number(item.inventory_consumed_quantity || 0) > 0
    || Number(item.inventory_reserved_quantity || 0) > 0;
};

const inventoryStatusText = (item) => {
  const reserved = Number(item.inventory_reserved_quantity || 0);
  const consumed = Number(item.inventory_consumed_quantity || 0);
  const shortage = Number(item.inventory_shortage_quantity || 0);
  const activeRequests = (item.purchase_requests || []).filter(request => !['CANCELED', 'ASSIGNED_TO_WORK_ORDER'].includes(request.status));
  const quantity = Number(item.quantity || 0);

  if (consumed >= quantity && quantity > 0) return `已扣庫存 ${consumed}`;
  if (selectedWorkOrder.value?.inventory_reservation_pending && reserved <= 0 && consumed <= 0) return '待主管確認預留';
  if (selectedWorkOrder.value?.inventory_consumption_pending && reserved > 0) return `待主管確認扣庫存 / 已預留 ${reserved}`;
  if (shortage > 0 && activeRequests.length) return `已預留 ${reserved} / 已扣 ${consumed} / 缺貨待到貨 ${shortage}`;
  if (shortage > 0) return `已預留 ${reserved} / 已扣 ${consumed} / 缺貨 ${shortage}`;
  if (reserved > 0) return `已預留 ${reserved} / 待扣庫存`;
  if (consumed > 0) return `已扣庫存 ${consumed}`;
  return '尚未預留';
};

const calculateTotal = (items) => {
  let subtotal = 0;
  let discount = 0;
  for (const item of items) {
    const amount = lineItemTotal(item);
    if (item.type === 'DISCOUNT') discount += amount;
    else subtotal += amount;
  }
  return Math.max(0, subtotal - discount);
};

const calculateMembershipTotal = (items) => {
  let subtotal = 0;
  let discount = 0;
  for (const item of items) {
    if (!item.counts_toward_membership) continue;
    const amount = lineItemTotal(item);
    if (item.type === 'DISCOUNT') discount += amount;
    else subtotal += amount;
  }
  return Math.min(calculateTotal(items), Math.max(0, subtotal - discount));
};

const cleanLineItem = (item) => ({
  id: item.id || undefined,
  type: item.type,
  name: item.name || (item.type === 'DISCOUNT' ? '折扣' : ''),
  description: item.description || '',
  product_id: item.type === 'PART' ? Number(item.product_id) || null : null,
  quantity: Number(item.quantity),
  unit_price: Number(item.unit_price) || 0,
  is_confirmed: Number(item.is_confirmed ?? 1),
  counts_toward_membership: Boolean(item.counts_toward_membership)
});

const hasText = (value) => String(value ?? '').trim().length > 0;

const hasMileageValue = (value) => {
  if (value === null || value === undefined || value === '') return false;
  const mileage = Number(value);
  return Number.isFinite(mileage) && mileage >= 0;
};

const validateLineItems = (items) => {
  for (const [index, item] of items.entries()) {
    if (!hasText(item.name)) return `第 ${index + 1} 項明細：明細名稱為必填`;

    const quantity = Number(item.quantity);
    if (!Number.isFinite(quantity) || !Number.isInteger(quantity) || quantity <= 0) {
      return `第 ${index + 1} 項明細：數量必須是大於 0 的整數`;
    }
  }
  return '';
};

const validateCreateRequiredFields = () => {
  if (!hasText(createForm.value.vehicle_license_plate)) return '車牌為必填';
  if (!hasText(createForm.value.vehicle_model)) return '車型為必填';
  if (!hasMileageValue(createForm.value.vehicle_mileage)) return '里程為必填';
  if (!hasText(createForm.value.responsible_staff)) return '負責人為必填';
  return '';
};

const submitCreateWorkOrder = async () => {
  const validationMessage = validateCreateRequiredFields() || validateLineItems(createLineItems.value);
  if (validationMessage) {
    alert(validationMessage);
    return;
  }

  saving.value = true;
  try {
    const payload = {
      ...createForm.value,
      vehicle_mileage: Number(createForm.value.vehicle_mileage),
      vehicle_purchase_date: createForm.value.vehicle_purchase_date || null,
      scheduled_at: createForm.value.scheduled_at || null,
      line_items: createLineItems.value.map(cleanLineItem)
    };
    if (createSource.value === 'guest') {
      delete payload.google_id;
      delete payload.motor_id;
    } else {
      delete payload.guest_customer_id;
      delete payload.guest_motor_id;
      delete payload.guest_name;
      delete payload.guest_phone;
      delete payload.vehicle_is_new;
      delete payload.vehicle_purchase_date;
    }
    const created = await createWorkOrder(payload);
    closeCreateModal();
    await fetchWorkOrders();
    await openDetail(created.id);
  } catch (error) {
    alert(`建立工單失敗：${getErrorMessage(error)}`);
  } finally {
    saving.value = false;
  }
};

const openDetail = async (id) => {
  try {
    await Promise.all([fetchProducts(), fetchStaffAdmins()]);
    selectedWorkOrder.value = await getWorkOrder(id);
    detailForm.value = {
      service_type: selectedWorkOrder.value.service_type,
      status: selectedWorkOrder.value.status,
      problem_description: selectedWorkOrder.value.problem_description || '',
      inspection_result: selectedWorkOrder.value.inspection_result || '',
      responsible_staff: selectedWorkOrder.value.responsible_staff || defaultResponsibleStaff,
      scheduled_at: toDatetimeLocal(selectedWorkOrder.value.scheduled_at),
      consumption_date: selectedWorkOrder.value.consumption_date || '',
      notes: selectedWorkOrder.value.notes || ''
    };
    detailLineItems.value = (selectedWorkOrder.value.line_items || []).map(item => ({ ...item }));
    paymentForm.value = { amount: selectedWorkOrder.value.balance_amount || null, method: '', note: '' };
  } catch (error) {
    if (error.response?.status === 401) {
      authStore.adminLogout();
      alert('管理員登入已過期，請重新登入。');
      router.push('/admin-login');
      return;
    }
    alert(`讀取工單失敗：${getErrorMessage(error)}`);
  }
};

const closeDetail = () => {
  selectedWorkOrder.value = null;
  closeDeleteModal();
};

const saveWorkOrder = async () => {
  if (!selectedWorkOrder.value) return;
  if (!membershipSelectionLocked.value) {
    const validationMessage = validateLineItems(detailLineItems.value);
    if (validationMessage) {
      alert(validationMessage);
      return;
    }
  }
  saving.value = true;
  try {
    const payload = {
      ...detailForm.value,
      scheduled_at: detailForm.value.scheduled_at || null
    };
    if (!membershipSelectionLocked.value) {
      payload.line_items = detailLineItems.value.map(cleanLineItem);
    }
    selectedWorkOrder.value = await updateWorkOrder(selectedWorkOrder.value.id, payload);
    detailLineItems.value = (selectedWorkOrder.value.line_items || []).map(item => ({ ...item }));
    await fetchWorkOrders();
    alert('工單已儲存');
  } catch (error) {
    alert(`儲存失敗：${getErrorMessage(error)}`);
  } finally {
    saving.value = false;
  }
};

const submitPayment = async () => {
  if (!selectedWorkOrder.value || !paymentForm.value.amount) return;
  try {
    selectedWorkOrder.value = await addWorkOrderPayment(selectedWorkOrder.value.id, paymentForm.value);
    paymentForm.value = { amount: selectedWorkOrder.value.balance_amount || null, method: '', note: '' };
    await fetchWorkOrders();
  } catch (error) {
    alert(`付款登錄失敗：${getErrorMessage(error)}`);
  }
};

const isGatedStatus = (status) => gatedStatuses.includes(status);
const hasBlockingApproval = (workOrder, targetStatus = null) => {
  const pending = (workOrder.approvals || []).filter(approval => approval.status === 'PENDING');
  if (targetStatus === 'AWAITING_PAYMENT') {
    return pending.some(approval => approval.type !== 'INVENTORY_CONSUMPTION');
  }
  return pending.length > 0;
};

const updateLineItemFulfillment = async (item, status) => {
  if (!selectedWorkOrder.value || !item?.id || !status || !canReviewApprovals.value) return;
  updatingFulfillmentItemId.value = item.id;
  try {
    selectedWorkOrder.value = await updateWorkOrderLineItemFulfillmentStatus(
      selectedWorkOrder.value.id,
      item.id,
      status
    );
    detailLineItems.value = (selectedWorkOrder.value.line_items || []).map(item => ({ ...item }));
    await fetchWorkOrders();
  } catch (error) {
    alert(`明細狀態更新失敗：${getErrorMessage(error)}`);
  } finally {
    updatingFulfillmentItemId.value = null;
  }
};

const confirmSupervisorReview = async () => {
  if (!selectedWorkOrder.value || !canReviewApprovals.value || supervisorReviewLocked.value) return;
  reviewingWorkOrder.value = true;
  try {
    const payload = { reviewed_by: adminUser.value?.username || adminUser.value?.full_name || '主管' };
    selectedWorkOrder.value = await confirmWorkOrderReview(selectedWorkOrder.value.id, payload);
    detailLineItems.value = (selectedWorkOrder.value.line_items || []).map(item => ({ ...item }));
    await fetchWorkOrders();
  } catch (error) {
    alert(`確認審核失敗：${getErrorMessage(error)}`);
  } finally {
    reviewingWorkOrder.value = false;
  }
};

const openDeleteModal = () => {
  if (!selectedWorkOrder.value) return;
  deleteForm.value = { reason: '' };
  showDeleteModal.value = true;
};

const closeDeleteModal = () => {
  showDeleteModal.value = false;
  deleteForm.value = { reason: '' };
};

const confirmDeleteSelectedWorkOrder = async () => {
  if (!selectedWorkOrder.value || !deleteForm.value.reason) return;
  saving.value = true;
  try {
    await deleteWorkOrder(selectedWorkOrder.value.id, {
      reason: deleteForm.value.reason,
      actor: adminUser.value?.username || adminUser.value?.full_name || '管理員'
    });
    closeDeleteModal();
    closeDetail();
    await fetchWorkOrders();
  } catch (error) {
    alert(`刪除工單失敗：${getErrorMessage(error)}`);
  } finally {
    saving.value = false;
  }
};

const formatDateTime = (iso) => {
  if (!iso) return '-';
  const date = new Date(iso);
  return `${date.getFullYear()}/${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const formatDate = (value) => {
  if (!value) return '-';
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[1]}/${match[2]}/${match[3]}` : '-';
};

function todayDateString() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

const toDatetimeLocal = (iso) => {
  if (!iso) return '';
  const date = new Date(iso);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}T${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const getErrorMessage = (error) => {
  const detail = error.response?.data?.detail;
  if (!detail) return '未知錯誤';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg).join('\n');
  return JSON.stringify(detail);
};

watch(
  () => route.query,
  () => {
    readQuery();
    fetchWorkOrders();
  },
  { immediate: true }
);
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-work-orders {
  color: $text-primary;

  .section-header,
  .toolbar,
  .filter-bar,
  .search-box,
  .form-actions,
  .approval-actions,
  .modal-actions,
  .section-title-row,
  .payment-form {
    display: flex;
    gap: 0.7rem;
    flex-wrap: wrap;
  }

  .section-header {
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;

    h2 {
      color: $primary-light;
      margin: 0;
    }

    p {
      color: $text-secondary;
      margin: 0.35rem 0 0;
    }
  }

  .filter-bar,
  .toolbar {
    margin-bottom: 1rem;
    align-items: center;
  }

  .filter-bar {
    align-items: flex-end;

    .filter-control {
      min-width: 210px;

      span {
        font-weight: 700;
      }
    }

    .supervisor-filter-btn.active {
      border-color: $primary-color;
      color: $primary-light;
      background-color: rgba($primary-color, 0.14);
    }
  }

  .search-box {
    flex: 1 1 360px;

    input {
      flex: 1;
      min-width: 240px;
    }
  }

  input,
  select,
  textarea,
  .date-picker {
    padding: 0.62rem 0.72rem;
    background-color: $dark-grey;
    color: $text-primary;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    font-family: inherit;

    &:focus {
      outline: none;
      border-color: $primary-light;
    }
  }

  textarea {
    resize: vertical;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.38rem;
    color: $text-secondary;
    font-size: 0.88rem;
  }

  .field-label {
    display: inline-flex;
    align-items: center;
    gap: 0.18rem;
  }

  .required-mark {
    color: $primary-light;
    font-weight: 800;
  }

  .new-vehicle-field span {
    min-height: 39px;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: $text-primary;

    input {
      width: 18px;
      height: 18px;
      padding: 0;
    }
  }

  .btn {
    padding: 0.58rem 0.95rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.05);
    color: $text-secondary;
    border-radius: $border-radius;
    cursor: pointer;
    font-weight: 700;
    white-space: nowrap;

    &:disabled {
      cursor: not-allowed;
      opacity: 0.48;
    }
  }

  .btn-primary {
    background-color: $primary-color;
    color: #fff;
    border-color: $primary-color;
  }

  .btn-outline {
    border-color: $medium-grey;
    color: $primary-light;
  }

  .btn-ghost {
    background: transparent;
    color: $text-secondary;
  }

  .icon-btn {
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: $border-radius;
    background: rgba(255, 255, 255, 0.06);
    color: $text-primary;
    cursor: pointer;

    &.danger {
      color: #ff7676;
    }
  }

  .table-wrap {
    background-color: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    overflow: auto;
  }

  .work-order-table,
  .mini-table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      padding: 0.85rem 1rem;
      text-align: left;
      border-bottom: 1px solid $medium-grey;
      white-space: nowrap;
      vertical-align: top;
    }

    th {
      background-color: $background-color;
      color: $text-secondary;
      font-size: 0.86rem;
      font-weight: 600;
    }
  }

  .work-order-table tbody tr {
    cursor: pointer;

    &:hover {
      background-color: rgba($primary-color, 0.06);
    }
  }

  .strong-cell,
  .amount {
    color: $primary-light;
    font-weight: 700;
  }

  .secondary-line,
  .muted-line {
    display: block;
    margin-top: 0.22rem;
    color: $text-secondary;
    font-size: 0.82rem;
    font-weight: 400;
  }

  .status-tag,
  .payment-tag {
    display: inline-flex;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.8rem;
    background-color: rgba($medium-grey, 0.4);
  }

  .INSPECTION_PENDING,
  .PENDING,
  .UNPAID { color: #ffc107; background-color: rgba(#ffc107, 0.15); }
  .QUOTE_PENDING,
  .CUSTOMER_CONFIRMATION_PENDING,
  .PARTIALLY_PAID { color: #ff9800; background-color: rgba(#ff9800, 0.15); }
  .SUPERVISOR_APPROVAL_PENDING { color: #ce93d8; background-color: rgba(#ce93d8, 0.15); }
  .IN_PROGRESS { color: #64b5f6; background-color: rgba(#64b5f6, 0.15); }
  .AWAITING_PAYMENT { color: #ffb74d; background-color: rgba(#ffb74d, 0.15); }
  .COMPLETED,
  .PAID { color: #4caf50; background-color: rgba(#4caf50, 0.15); }
  .CANCELED,
  .REFUNDED { color: #e57373; background-color: rgba(#e57373, 0.15); }

  .loading,
  .empty-state {
    padding: 3rem;
    text-align: center;
    color: $text-disabled;
  }

  .modal-overlay {
    position: fixed;
    inset: 0;
    background-color: rgba(0, 0, 0, 0.72);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    overflow: auto;
    padding: 4vh 1rem;
    z-index: 1000;

    &.confirm-overlay {
      align-items: center;
      z-index: 1010;
    }
  }

  .modal-content {
    box-sizing: border-box;
    width: min(96vw, 920px);
    background-color: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    padding: 1.5rem;
    box-shadow: 0 18px 60px rgba(0, 0, 0, 0.45);

    &.large,
    &.xlarge {
      width: min(98vw, 1180px);
    }

    &.confirm-modal {
      width: min(92vw, 520px);
    }
  }

  .modal-footer-actions {
    justify-content: flex-end;
    margin-top: 1rem;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1rem;

    h3 {
      color: $primary-light;
      margin: 0;
    }

    p {
      color: $text-secondary;
      margin: 0.3rem 0 0;
    }
  }

  .work-order-form,
  .detail-grid {
    display: grid;
    gap: 1rem;
  }

  .detail-grid {
    grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.8fr);
  }

  .form-section {
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    padding: 1rem;
    background-color: $background-color;
    display: grid;
    gap: 0.9rem;

    h4 {
      color: $primary-light;
      margin: 0;
    }
  }

  .form-grid,
  .source-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.8rem;
  }

  .form-row {
    grid-column: 1 / -1;
  }

  .search-row {
    display: flex;
    gap: 0.7rem;

    input {
      flex: 1;
    }
  }

  .segmented {
    display: inline-flex;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    overflow: hidden;
    width: fit-content;

    button {
      border: none;
      padding: 0.55rem 1rem;
      background: transparent;
      color: $text-secondary;
      cursor: pointer;

      &.active {
        background: rgba($primary-color, 0.16);
        color: $primary-light;
      }
    }
  }

  .result-list {
    grid-column: 1 / -1;
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;

    button {
      border: 1px solid $medium-grey;
      background: rgba(255, 255, 255, 0.04);
      color: $text-primary;
      border-radius: $border-radius;
      padding: 0.45rem 0.7rem;
      cursor: pointer;
    }
  }

  .line-editor {
    display: grid;
    gap: 0.55rem;
    container-type: inline-size;
  }

  .line-row {
    display: grid;
    grid-template-columns: 96px minmax(130px, 0.9fr) minmax(160px, 1.35fr) 68px 80px 132px 104px 36px;
    gap: 0.5rem;
    align-items: end;
    min-width: 0;

    .line-type { grid-column: 1; }
    .line-product { grid-column: 2; }
    .line-name { grid-column: 3; }
    .line-quantity { grid-column: 4; }
    .line-price { grid-column: 5; }

    .line-field {
      display: grid;
      gap: 0.28rem;
      min-width: 0;

      span {
        color: $text-secondary;
        font-size: 0.78rem;
        font-weight: 700;
      }

      input,
      select {
        box-sizing: border-box;
        width: 100%;
        max-width: 100%;
        min-width: 0;
      }
    }

    .line-total {
      grid-column: 7;
      grid-row: 1;
      display: grid;
      gap: 0.28rem;
      color: $primary-light;
      font-weight: 700;
      white-space: nowrap;

      > span {
        color: $text-secondary;
        font-size: 0.78rem;
        font-weight: 700;
      }

      strong {
        min-height: 42px;
        display: inline-flex;
        align-items: center;
      }

      small {
        display: block;
        color: $text-secondary;
        font-weight: 400;
      }
    }

    .membership-toggle {
      grid-column: 6;
      grid-row: 1;
      justify-self: stretch;
      min-height: 42px;
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 0.5rem;
      padding: 0.55rem 0.65rem;
      box-sizing: border-box;
      border: 1px solid $medium-grey;
      border-radius: $border-radius;
      color: $text-primary;
      cursor: pointer;

      input {
        width: 18px;
        height: 18px;
        accent-color: $primary-color;
      }

      span {
        font-size: 0.78rem;
        font-weight: 700;
        line-height: 1.25;
      }
    }

    > .icon-btn {
      grid-column: 8;
      grid-row: 1;
    }
  }

  .line-status-table-wrap {
    overflow-x: auto;
  }

  .line-status-heading {
    align-items: center;
    justify-content: space-between;
  }

  .reviewed-label {
    color: #81c784;
    font-weight: 700;
  }

  .line-status-table {
    min-width: 680px;

    th:nth-child(2),
    td:nth-child(2) {
      width: 42%;
      white-space: normal;
    }

    select {
      min-width: 120px;
    }
  }

  @container (max-width: 900px) {
    .line-row {
      grid-template-columns: repeat(12, minmax(0, 1fr));
      row-gap: 0.65rem;

      .line-type { grid-column: 1 / span 2; }
      .line-product { grid-column: 3 / span 3; }
      .line-name { grid-column: 6 / span 3; }
      .line-quantity { grid-column: 9 / span 2; }
      .line-price { grid-column: 11 / span 2; }

      .membership-toggle {
        grid-column: 1 / span 4;
        grid-row: 2;
      }

      .line-total {
        grid-column: 9 / span 3;
        grid-row: 2;
        justify-self: end;
        min-width: 96px;
      }

      > .icon-btn {
        grid-column: 12;
        grid-row: 2;
        justify-self: end;
      }
    }
  }

  .total-row {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    align-items: center;
    color: $text-secondary;

    strong {
      color: $primary-light;
      font-size: 1.1rem;
    }
  }

  .membership-total strong {
    color: #66bb6a;
  }

  .money-summary {
    display: grid;
    gap: 0.6rem;
    margin: 0;

    div {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
    }

    dt {
      color: $text-secondary;
    }

    dd {
      margin: 0;
      color: $primary-light;
      font-weight: 700;
    }
  }

  .warning-text {
    color: #ffb74d;
    background-color: rgba(#ffb74d, 0.1);
    border: 1px solid rgba(#ffb74d, 0.25);
    border-radius: $border-radius;
    padding: 0.75rem;
  }

  @media (max-width: 980px) {
    .filter-bar {
      align-items: stretch;

      .filter-control,
      .supervisor-filter-btn {
        width: 100%;
      }
    }

    .detail-grid,
    .form-grid,
    .source-grid {
      grid-template-columns: 1fr;
    }

    .line-row {
      grid-template-columns: 1fr;
      align-items: stretch;

      .line-type,
      .line-product,
      .line-name,
      .line-quantity,
      .line-price {
        grid-column: auto;
      }

      .line-total,
      .membership-toggle,
      > .icon-btn {
        grid-column: auto;
        grid-row: auto;
      }

      .membership-toggle {
        justify-self: stretch;
      }
    }
  }
}
</style>
