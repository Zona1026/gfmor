<template>
  <div class="new-vehicles-page">
    <header class="section-header">
      <div>
        <h2>新車專區</h2>
        <p>管理新車定期保養里程表，此處紀錄不列入消費與點數。</p>
      </div>
      <div class="search-bar">
        <input v-model.trim="keyword" type="search" placeholder="搜尋車主、電話、車牌或車型" @keyup.enter="fetchProfiles" />
        <button type="button" @click="fetchProfiles">搜尋</button>
      </div>
    </header>

    <div v-if="loading" class="state-message">載入新車名冊中...</div>
    <div v-else-if="profiles.length === 0" class="state-message">
      尚無新車資料，請在新增或編輯車輛時勾選「新車」。
    </div>

    <div v-else class="workspace">
      <aside class="vehicle-list" aria-label="新車名冊">
        <button
          v-for="profile in profiles"
          :key="profileKey(profile)"
          type="button"
          :class="{ active: profileKey(profile) === selectedKey }"
          @click="selectProfile(profile)"
        >
          <strong>{{ profile.license_plate }}</strong>
          <span>{{ profile.customer_name }} / {{ [profile.brand, profile.model_name].filter(Boolean).join(' ') || '未填車型' }}</span>
          <small>{{ profile.vehicle_type === 'member' ? '會員' : '散客' }}</small>
        </button>
      </aside>

      <section v-if="selectedProfile" class="maintenance-sheet">
        <div class="vehicle-heading">
          <div>
            <h3>{{ selectedProfile.customer_name }}的新車保養紀錄</h3>
            <p>{{ selectedProfile.customer_phone || '未填電話' }}</p>
          </div>
          <span class="vehicle-type">{{ selectedProfile.vehicle_type === 'member' ? '會員車輛' : '散客車輛' }}</span>
        </div>

        <dl class="vehicle-summary">
          <div><dt>車牌號碼</dt><dd>{{ selectedProfile.license_plate }}</dd></div>
          <div><dt>廠牌 / 車型</dt><dd>{{ [selectedProfile.brand, selectedProfile.model_name].filter(Boolean).join(' ') || '未填' }}</dd></div>
          <div><dt>購車日期</dt><dd>{{ formatDate(selectedProfile.purchase_date) }}</dd></div>
          <div><dt>引擎號碼</dt><dd>{{ selectedProfile.vin || '未填' }}</dd></div>
        </dl>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>保養里程</th>
                <th>保養日期</th>
                <th>實際里程</th>
                <th>機油</th>
                <th>齒輪油</th>
                <th>空氣濾清器</th>
                <th>備註</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in selectedProfile.records" :key="record.id">
                <td class="target-mileage">{{ formatNumber(record.target_mileage) }} km</td>
                <td><input v-model="drafts[record.id].service_date" type="date" aria-label="保養日期" /></td>
                <td><input v-model.number="drafts[record.id].actual_mileage" type="number" min="0" inputmode="numeric" aria-label="實際里程" /></td>
                <td><input v-model="drafts[record.id].engine_oil" type="checkbox" aria-label="更換機油" /></td>
                <td><input v-model="drafts[record.id].gear_oil" type="checkbox" aria-label="更換齒輪油" /></td>
                <td><input v-model="drafts[record.id].air_filter" type="checkbox" aria-label="保養空氣濾清器" /></td>
                <td><input v-model.trim="drafts[record.id].notes" type="text" maxlength="255" placeholder="保養項目或備註" /></td>
                <td>
                  <button type="button" class="save-button" :disabled="savingId === record.id" @click="saveRecord(record)">
                    {{ savingId === record.id ? '儲存中' : '儲存' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { getNewVehicleProfiles, updateNewVehicleMaintenanceRecord } from '../../api/admin';

const profiles = ref([]);
const keyword = ref('');
const selectedKey = ref('');
const drafts = ref({});
const loading = ref(false);
const savingId = ref(null);
const VEHICLE_DATA_UPDATED_KEY = 'vehicleDataUpdatedAt';

const profileKey = (profile) => `${profile.vehicle_type}-${profile.vehicle_id}`;
const selectedProfile = computed(() => profiles.value.find(profile => profileKey(profile) === selectedKey.value) || null);
const formatNumber = (value) => Number(value || 0).toLocaleString();
const formatDate = (value) => value ? String(value).replaceAll('-', '/') : '未填';

const makeDraft = (record) => ({
  service_date: record.service_date || '',
  actual_mileage: record.actual_mileage ?? null,
  engine_oil: Boolean(record.engine_oil),
  gear_oil: Boolean(record.gear_oil),
  air_filter: Boolean(record.air_filter),
  notes: record.notes || ''
});

const selectProfile = (profile) => {
  selectedKey.value = profileKey(profile);
  drafts.value = Object.fromEntries(profile.records.map(record => [record.id, makeDraft(record)]));
};

const fetchProfiles = async () => {
  loading.value = true;
  try {
    profiles.value = await getNewVehicleProfiles({ q: keyword.value || undefined });
    const current = profiles.value.find(profile => profileKey(profile) === selectedKey.value) || profiles.value[0];
    if (current) selectProfile(current);
    else selectedKey.value = '';
  } catch (error) {
    profiles.value = [];
    alert(error.response?.data?.detail || '載入新車名冊失敗');
  } finally {
    loading.value = false;
  }
};

const handleVehicleStorageUpdate = (event) => {
  if (event.key === VEHICLE_DATA_UPDATED_KEY) fetchProfiles();
};

const handleVisibilityChange = () => {
  if (document.visibilityState === 'visible') fetchProfiles();
};

const saveRecord = async (record) => {
  const profile = selectedProfile.value;
  if (!profile) return;

  savingId.value = record.id;
  try {
    const draft = drafts.value[record.id];
    const updated = await updateNewVehicleMaintenanceRecord(
      profile.vehicle_type,
      profile.vehicle_id,
      record.id,
      {
        ...draft,
        service_date: draft.service_date || null,
        actual_mileage: draft.actual_mileage === '' ? null : draft.actual_mileage,
        notes: draft.notes || null
      }
    );
    Object.assign(record, updated);
    drafts.value[record.id] = makeDraft(updated);
    localStorage.setItem(VEHICLE_DATA_UPDATED_KEY, String(Date.now()));
  } catch (error) {
    alert(error.response?.data?.detail || '儲存保養紀錄失敗');
  } finally {
    savingId.value = null;
  }
};

onMounted(() => {
  fetchProfiles();
  window.addEventListener('storage', handleVehicleStorageUpdate);
  window.addEventListener('focus', fetchProfiles);
  document.addEventListener('visibilitychange', handleVisibilityChange);
});

onBeforeUnmount(() => {
  window.removeEventListener('storage', handleVehicleStorageUpdate);
  window.removeEventListener('focus', fetchProfiles);
  document.removeEventListener('visibilitychange', handleVisibilityChange);
});
</script>

<style lang="scss" scoped>
@use '../../assets/_variables.scss' as *;

.new-vehicles-page {
  color: $text-primary;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
  margin-bottom: 1.5rem;

  h2 { margin: 0 0 0.35rem; color: $primary-color; }
  p { margin: 0; color: $text-secondary; }
}

.search-bar {
  display: flex;
  gap: 0.5rem;

  input {
    width: min(340px, 42vw);
    min-width: 0;
    padding: 0.65rem 0.8rem;
    border: 1px solid $medium-grey;
    background: $background-color;
    color: $text-primary;
  }

  button {
    flex: 0 0 64px;
    border: 0;
    padding: 0.65rem 1rem;
    background: $primary-color;
    color: #fff;
    cursor: pointer;
    white-space: nowrap;
  }
}

.state-message {
  min-height: 260px;
  display: grid;
  place-items: center;
  border: 1px solid $medium-grey;
  color: $text-disabled;
}

.workspace {
  border: 1px solid $medium-grey;
  min-height: 600px;
}

.vehicle-list {
  display: flex;
  overflow-x: auto;
  border-bottom: 1px solid $medium-grey;
  background: $background-color;

  button {
    min-width: 240px;
    display: grid;
    gap: 0.3rem;
    padding: 1rem;
    border: 0;
    border-right: 1px solid $medium-grey;
    border-bottom: 3px solid transparent;
    background: transparent;
    color: $text-primary;
    text-align: left;
    cursor: pointer;

    &:hover,
    &.active {
      border-bottom-color: $primary-color;
      background: rgba($primary-color, 0.1);
    }

    span,
    small { color: $text-secondary; }
  }
}

.maintenance-sheet {
  min-width: 0;
  padding: 1.25rem;
}

.vehicle-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;

  h3 { margin: 0 0 0.3rem; color: $primary-light; }
  p { margin: 0; color: $text-secondary; }
}

.vehicle-type {
  padding: 0.3rem 0.55rem;
  border: 1px solid $medium-grey;
  color: $text-secondary;
  font-size: 0.82rem;
}

.vehicle-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin: 1.25rem 0;
  background: $medium-grey;
  border: 1px solid $medium-grey;

  div { padding: 0.8rem; background: $dark-grey; }
  dt { color: $text-disabled; font-size: 0.78rem; }
  dd { margin: 0.25rem 0 0; font-weight: 700; }
}

.table-wrap { overflow-x: auto; }

table {
  width: 100%;
  min-width: 900px;
  border-collapse: collapse;

  th,
  td {
    padding: 0.55rem;
    border-bottom: 1px solid $medium-grey;
    text-align: left;
    white-space: nowrap;
  }

  th { color: $text-secondary; font-size: 0.8rem; }
  td { font-size: 0.86rem; }

  input[type='date'],
  input[type='number'],
  input[type='text'] {
    width: 100%;
    min-width: 110px;
    box-sizing: border-box;
    padding: 0.45rem 0.55rem;
    border: 1px solid $medium-grey;
    background: $background-color;
    color: $text-primary;
  }

  input[type='text'] { min-width: 180px; }
  input[type='checkbox'] { width: 18px; height: 18px; }
}

.target-mileage { color: $primary-light; font-weight: 700; }

.save-button {
  border: 1px solid $primary-color;
  padding: 0.45rem 0.7rem;
  background: transparent;
  color: $primary-light;
  cursor: pointer;

  &:disabled { opacity: 0.55; cursor: wait; }
}

@media (max-width: 900px) {
  .section-header { align-items: stretch; flex-direction: column; }
  .search-bar input { width: 100%; }
  .vehicle-list button { min-width: 220px; }
  .vehicle-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .search-bar { width: 100%; }
  .maintenance-sheet { padding: 0.8rem; }
  .vehicle-heading { flex-direction: column; }
  .vehicle-summary { grid-template-columns: 1fr; }
}
</style>
