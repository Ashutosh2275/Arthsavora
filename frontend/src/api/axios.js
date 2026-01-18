import axios from 'axios';

// Use environment variable for production readiness
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Production Error Handling Interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/auth';
    }
    if (error.response?.status === 429) {
      alert("System Busy: Too many requests. Please wait 60 seconds.");
    }
    return Promise.reject(error);
  }
);

export default api;