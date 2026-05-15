<template>
  <div class="admin-members">
    <div class="section-header">
      <h2>會員管理</h2>
      <div class="search-bar">
        <input 
          type="text" 
          v-model="searchKeyword" 
          placeholder="搜尋姓名 / 電話 / Email..." 
        />
      </div>
    </div>

    <div v-if="loading" class="loading">載入中...</div>

    <table v-else class="members-table">
      <thead>
        <tr>
          <th>姓名</th>
          <th>電話</th>
          <th>加入時間</th>
          <th>愛車數量</th>
          <th>累積消費</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="member in filteredMembers" :key="member.google_id">
          <td>
            <div class="member-name">
              <img 
                v-if="member.avatar" 
                :src="member.avatar" 
                class="avatar" 
                alt="avatar" 
              />
              <div v-else class="avatar placeholder-avatar">{{ member.name?.charAt(0) }}</div>
              {{ member.name }}
            </div>
          </td>
          <td>{{ member.phone || '—' }}</td>
          <td>{{ formatDate(member.join_time) }}</td>
          <td>{{ member.motors?.length || 0 }}</td>
          <td>$ {{ member.cumulative_consumption?.toLocaleString() || 0 }}</td>
          <td class="action-cell">
            <button class="btn btn-sm" @click="openDetailModal(member)">詳情</button>
            <button class="btn btn-sm" @click="openNoteModal(member)">
              <span v-if="member.admin_notes" class="has-note-dot"></span>
              註記
            </button>
          </td>
        </tr>
        <tr v-if="filteredMembers.length === 0">
          <td colspan="6" class="empty-row">查無符合條件的會員</td>
        </tr>
      </tbody>
    </table>

    <!-- 會員詳情 Modal -->
    <div class="modal-overlay" v-if="showDetailModal" @click.self="showDetailModal = false">
      <div class="modal modal-wide">
        <h3>會員詳情 — {{ detailMember?.name }}</h3>
        <div class="detail-section">
          <div class="detail-row">
            <span class="detail-label">Email</span>
            <span>{{ detailMember?.email }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">電話</span>
            <span>{{ detailMember?.phone || '—' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">加入時間</span>
            <span>{{ formatDate(detailMember?.join_time) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">累積消費</span>
            <span>$ {{ detailMember?.cumulative_consumption?.toLocaleString() || 0 }}</span>
          </div>
        </div>

        <h4>車輛資訊</h4>
        <table class="motors-table" v-if="detailMember?.motors?.length">
          <thead>
            <tr>
              <th>廠牌</th>
              <th>型號</th>
              <th>車牌</th>
              <th>引擎號碼</th>
              <th>里程 (km)</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="motor in detailMember.motors" :key="motor.id">
              <td>{{ motor.brand || '—' }}</td>
              <td>{{ motor.model_name || '—' }}</td>
              <td>{{ motor.license_plate || '—' }}</td>
              <td>
                <span v-if="editingMotorId !== motor.id">{{ motor.vin || '—' }}</span>
                <input 
                  v-else
                  type="text" 
                  v-model="motor.vin" 
                  class="inline-input" 
                  placeholder="輸入引擎號碼" 
                />
              </td>
              <td>
                <span v-if="editingMotorId !== motor.id">{{ motor.mileage?.toLocaleString() || '—' }}</span>
                <input 
                  v-else
                  type="number" 
                  v-model.number="motor.mileage" 
                  class="inline-input" 
                  placeholder="輸入里程" 
                />
              </td>
              <td>
                <button 
                  v-if="editingMotorId !== motor.id" 
                  class="btn btn-sm" 
                  @click="editingMotorId = motor.id"
                >編輯</button>
                <button 
                  v-else 
                  class="btn btn-sm btn-save" 
                  @click="saveMotor(motor)"
                >儲存</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-muted">此會員尚未登記車輛。</p>

        <div class="form-actions">
          <button type="button" class="btn btn-outline" @click="showDetailModal = false">關閉</button>
        </div>
      </div>
    </div>

    <!-- 會員註記 Modal -->
    <div class="modal-overlay" v-if="showNoteModal" @click.self="showNoteModal = false">
      <div class="modal">
        <h3>會員註記 — {{ editingMember?.name }}</h3>
        <p class="text-muted">此註記僅店家可見，客戶端不會顯示。</p>
        <textarea 
          v-model="editingNotes" 
          rows="6"
          placeholder="記錄該客戶的偏好、注意事項等..."
        ></textarea>
        <div class="form-actions">
          <button type="button" class="btn btn-outline" @click="showNoteModal = false">取消</button>
          <button type="button" class="btn btn-primary" @click="saveNotes" :disabled="savingNotes">
            {{ savingNotes ? '儲存中...' : '儲存註記' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { getMembers, updateMemberNotes } from '../../api/admin';
import api from '../../api/index';

const loading = ref(false);
const members = ref([]);
const searchKeyword = ref('');

// Note Modal
const showNoteModal = ref(false);
const editingMember = ref(null);
const editingNotes = ref('');
const savingNotes = ref(false);

// Detail Modal
const showDetailModal = ref(false);
const detailMember = ref(null);
const editingMotorId = ref(null);

const filteredMembers = computed(() => {
  if (!searchKeyword.value) return members.value;
  const kw = searchKeyword.value.toLowerCase();
  return members.value.filter(m => 
    (m.name && m.name.toLowerCase().includes(kw)) ||
    (m.phone && m.phone.includes(kw)) ||
    (m.email && m.email.toLowerCase().includes(kw))
  );
});

const formatDate = (isoString) => {
  if (!isoString) return '';
  const d = new Date(isoString);
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
};

const fetchMembers = async () => {
  loading.value = true;
  try {
    const data = await getMembers();
    // filter out system ghost user
    members.value = (data || []).filter(m => m.google_id !== 'system');
  } catch (e) {
    console.error('載入會員失敗', e);
  } finally {
    loading.value = false;
  }
};

const openNoteModal = (member) => {
  editingMember.value = member;
  editingNotes.value = member.admin_notes || '';
  showNoteModal.value = true;
};

const openDetailModal = (member) => {
  detailMember.value = member;
  editingMotorId.value = null;
  showDetailModal.value = true;
};

const saveMotor = async (motor) => {
  try {
    await api.put(`/motors/${motor.id}`, {
      vin: motor.vin || null,
      mileage: motor.mileage || null
    });
    alert('車輛資料已更新！');
    editingMotorId.value = null;
  } catch (e) {
    console.error(e);
    alert('更新失敗，請稍後再試');
  }
};

const saveNotes = async () => {
  if (!editingMember.value) return;
  savingNotes.value = true;
  try {
    await updateMemberNotes(editingMember.value.google_id, editingNotes.value);
    // Sync local state
    editingMember.value.admin_notes = editingNotes.value;
    alert('註記已儲存！');
    showNoteModal.value = false;
  } catch (e) {
    console.error(e);
    alert('儲存失敗，請稍後再試');
  } finally {
    savingNotes.value = false;
  }
};

onMounted(fetchMembers);
</script>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.admin-members {
  color: $text-primary;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
    gap: 1rem;

    h2 {
      color: $primary-light;
      margin: 0;
    }

    .search-bar input {
      padding: 0.6rem 1rem;
      background-color: $background-color;
      border: 1px solid $medium-grey;
      border-radius: $border-radius;
      color: $text-primary;
      font-size: 0.95rem;
      width: 280px;

      &::placeholder { color: $text-disabled; }
      &:focus {
        outline: none;
        border-color: $primary-color;
      }
    }
  }

  .loading {
    text-align: center;
    padding: 3rem;
    color: $text-secondary;
  }

  .members-table {
    width: 100%;
    border-collapse: collapse;
    background-color: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: $border-radius;
    overflow: hidden;

    th, td {
      padding: 0.85rem 1rem;
      text-align: left;
      border-bottom: 1px solid $medium-grey;
      white-space: nowrap;
    }

    th {
      background-color: $background-color;
      color: $text-secondary;
      font-weight: 600;
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }

    tbody tr {
      transition: background-color 0.2s;
      &:hover {
        background-color: rgba($primary-color, 0.05);
      }
    }

    .member-name {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-weight: 500;
    }

    .avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      object-fit: cover;
    }

    .placeholder-avatar {
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: $medium-grey;
      color: $text-primary;
      font-weight: bold;
      font-size: 0.85rem;
    }

    .empty-row {
      text-align: center;
      color: $text-disabled;
      padding: 2rem;
    }
  }

  .btn {
    padding: 0.4rem 0.9rem;
    border: 1px solid $primary-color;
    background-color: transparent;
    color: $primary-color;
    border-radius: $border-radius;
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.2s;
    position: relative;

    &:hover {
      background-color: $primary-color;
      color: #fff;
    }

    .has-note-dot {
      position: absolute;
      top: -3px;
      right: -3px;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: #4caf50;
    }
  }

  .action-cell {
    display: flex;
    gap: 0.5rem;
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6);
    z-index: 1000;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .modal {
    background-color: $dark-grey;
    border: 1px solid $medium-grey;
    border-radius: 8px;
    padding: 2rem;
    width: 500px;
    max-width: 90%;

    &.modal-wide {
      width: 700px;
    }

    h3 {
      color: $primary-light;
      margin: 0 0 0.3rem 0;
    }

    h4 {
      color: $text-secondary;
      margin: 1.5rem 0 0.8rem 0;
      font-size: 1rem;
    }

    .detail-section {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      margin-top: 1rem;
    }

    .detail-row {
      display: flex;
      gap: 1rem;

      .detail-label {
        min-width: 80px;
        color: $text-disabled;
        font-weight: 600;
      }
    }

    .motors-table {
      width: 100%;
      border-collapse: collapse;
      border: 1px solid $medium-grey;
      border-radius: $border-radius;
      overflow: hidden;

      th, td {
        padding: 0.6rem 0.8rem;
        text-align: left;
        border-bottom: 1px solid $medium-grey;
        font-size: 0.9rem;
      }

      th {
        background-color: $background-color;
        color: $text-disabled;
        font-weight: 600;
      }

      .inline-input {
        width: 100%;
        padding: 0.4rem 0.6rem;
        background-color: $background-color;
        border: 1px solid $medium-grey;
        border-radius: $border-radius;
        color: $text-primary;
        font-size: 0.85rem;
        box-sizing: border-box;

        &:focus {
          outline: none;
          border-color: $primary-color;
        }
      }

      .btn-save {
        padding: 0.3rem 0.7rem;
        background-color: $primary-color;
        border: none;
        color: #fff;
        border-radius: $border-radius;
        cursor: pointer;
        font-size: 0.8rem;
        white-space: nowrap;
        &:hover { background: $primary-dark; }
      }
    }

    .text-muted {
      color: $text-disabled;
      font-size: 0.85rem;
      margin: 0 0 1rem 0;
    }

    textarea {
      width: 100%;
      padding: 0.8rem;
      background-color: $background-color;
      border: 1px solid $medium-grey;
      border-radius: $border-radius;
      color: $text-primary;
      font-size: 1rem;
      resize: vertical;
      box-sizing: border-box;

      &:focus {
        outline: none;
        border-color: $primary-color;
      }
    }

    .form-actions {
      display: flex;
      gap: 0.8rem;
      justify-content: flex-end;
      margin-top: 1rem;

      .btn-outline {
        padding: 0.5rem 1.2rem;
        background: transparent;
        border: 1px solid $medium-grey;
        color: $text-secondary;
        border-radius: $border-radius;
        cursor: pointer;
        &:hover { background: $medium-grey; }
      }

      .btn-primary {
        padding: 0.5rem 1.2rem;
        background: $primary-color;
        border: none;
        color: #fff;
        border-radius: $border-radius;
        cursor: pointer;
        font-weight: bold;
        &:hover { background: $primary-dark; }
        &:disabled { opacity: 0.5; cursor: not-allowed; }
      }
    }
  }
}
</style>
