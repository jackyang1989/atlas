import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 自动添加 token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 处理错误
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 401 未授权，清除 token 并重定向到登录
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ==================== Auth 认证接口 ====================
export const authAPI = {
  login: (username, password) =>
    apiClient.post('/api/auth/login', { username, password }),
  
  getCurrentUser: () =>
    apiClient.get('/api/auth/me'),
  
  changePassword: (oldPassword, newPassword) =>
    apiClient.post('/api/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    }),
};

// ==================== Services 服务管理接口 ====================
export const servicesAPI = {
  list: (skip = 0, limit = 10) =>
    apiClient.get('/api/services/', { params: { skip, limit } }),
  
  create: (data) =>
    apiClient.post('/api/services/', data),
  
  get: (serviceId) =>
    apiClient.get(`/api/services/${serviceId}`),
  
  update: (serviceId, data) =>
    apiClient.put(`/api/services/${serviceId}`, data),
  
  toggle: (serviceId) =>
    apiClient.put(`/api/services/${serviceId}/toggle`),
  
  delete: (serviceId) =>
    apiClient.delete(`/api/services/${serviceId}`),
};

// ==================== System 系统接口 ====================
export const systemAPI = {
  health: () =>
    apiClient.get('/health'),
  
  stats: () =>
    apiClient.get('/api/system/stats'),
};

export default apiClient;
