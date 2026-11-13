import axios, { type AxiosInstance } from 'axios';
import { toast } from 'sonner';

export const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail || error.response?.data?.error?.message;

    if (status === 401) {
      localStorage.removeItem('token');
      // If unauthorized and not already on /auth, redirect smoothly
      if (window.location.pathname !== '/auth') {
        window.location.href = '/auth';
      }
    } else if (status === 429) {
      toast.warning(detail || 'Rate limit exceeded. Please wait a moment.');
    } else if (status >= 500) {
      toast.error('An unexpected server error occurred. Please try again.');
    }

    return Promise.reject(error);
  }
);

export default api;
