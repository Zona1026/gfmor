import axios from 'axios';

// 1. 建立 Axios 實例
const apiClient = axios.create({
  // 從 Vite 的環境變數中讀取後端 API 的基礎網址
  // import.meta.env.VITE_API_URL 的值是 "http://127.0.0.1:8000/api"
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 2. 請求攔截器 (Request Interceptor)
// 未來會在此處加入邏輯，自動在每個請求的 header 中附上 JWT
apiClient.interceptors.request.use(
  (config) => {
    const adminToken = localStorage.getItem('adminToken');
    const userToken = localStorage.getItem('token');
    
    // 依據請求路徑決定帶哪種 Token
    const isRequestAdmin = config.url && config.url.includes('/admin/');
    if (isRequestAdmin && adminToken) {
      config.headers.Authorization = `Bearer ${adminToken}`;
    } else if (userToken) {
      config.headers.Authorization = `Bearer ${userToken}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 3. 回應攔截器 (Response Interceptor)
// 未來可用於統一處理錯誤，例如 401 未授權時自動導向到登入頁
apiClient.interceptors.response.use(
  (response) => {
    // 只回傳 response.data，簡化在組件中使用的層級
    return response.data;
  },
  (error) => {
    // 在此處可以處理各種 HTTP 錯誤
    // 例如：
    // if (error.response.status === 401) {
    //   // 導向到登入頁
    // }
    return Promise.reject(error);
  }
);

export default apiClient;
