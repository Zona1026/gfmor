import { defineStore } from 'pinia';
import api from '../api/index';

export const useSiteStore = defineStore('site', {
  state: () => ({
    settings: {
      store_name: '炬烽騎士精品',
      store_address: '載入中...',
      store_phone: '載入中...',
      business_hours: '載入中...',
      footer_description: '專業二輪維修、保養與精品改裝。提供最值得信賴的技術與服務。'
    },
    loading: false
  }),
  actions: {
    async fetchSettings() {
      this.loading = true;
      try {
        const data = await api.get('/settings/');
        if (data) {
          this.settings = { ...this.settings, ...data };
        }
      } catch (error) {
        console.error('Failed to fetch site settings', error);
      } finally {
        this.loading = false;
      }
    },
    async updateSettings(newSettings) {
      try {
        await api.put('/settings/', newSettings);
        this.settings = { ...this.settings, ...newSettings };
        return true;
      } catch (error) {
        console.error('Failed to update site settings', error);
        throw error;
      }
    }
  }
});
