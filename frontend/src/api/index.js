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

let isRedirectingToAdminLogin = false;

const isAdminPage = () => {
  const currentPath = window.location.pathname;
  return currentPath === '/admin' || currentPath.startsWith('/admin/');
};

const redirectToAdminLogin = () => {
  localStorage.removeItem('adminToken');
  localStorage.removeItem('adminUser');
  localStorage.removeItem('adminLastActivityAt');

  if (!isRedirectingToAdminLogin) {
    isRedirectingToAdminLogin = true;
    window.location.replace('/admin-login');
  }
};

// 2. 請求攔截器 (Request Interceptor)
// 未來會在此處加入邏輯，自動在每個請求的 header 中附上 JWT
apiClient.interceptors.request.use(
  (config) => {
    const adminToken = localStorage.getItem('adminToken');
    const userToken = localStorage.getItem('token');
    const isAdminRoute = isAdminPage();
    
    // 後台頁面才優先帶 adminToken；會員中心與一般會員流程應使用 user token。
    // 這可避免手機瀏覽器殘留的後台 token 影響會員新增/修改車輛。
    const hasAuthHeader = config.headers?.Authorization || config.headers?.authorization;
    if (!hasAuthHeader) {
      if (isAdminRoute && adminToken) {
        config.headers.Authorization = `Bearer ${adminToken}`;
      } else if (userToken) {
        config.headers.Authorization = `Bearer ${userToken}`;
      }
    }
    
    // Axios 遇到開頭為 / 的路徑會忽略 baseURL 裡面的路徑 (例如 /api)
    // 這裡攔截並強制把它跟 baseURL 接起來
    if (config.url && config.url.startsWith('/')) {
      config.url = import.meta.env.VITE_API_URL + config.url;
      config.baseURL = ''; 
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 3. 回應攔截器 (Response Interceptor)
apiClient.interceptors.response.use(
  (response) => {
    // 只回傳 response.data，簡化在組件中使用的層級
    return response.data;
  },
  (error) => {
    if (error.response?.status === 401 && isAdminPage()) {
      redirectToAdminLogin();

      // The page is unloading. Keep the rejected request from reaching page-level
      // handlers that would otherwise display an alert before the redirect.
      return new Promise(() => {});
    }

    return Promise.reject(error);
  }
);

export default apiClient;
