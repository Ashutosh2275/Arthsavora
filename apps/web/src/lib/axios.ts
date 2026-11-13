import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import { toast } from 'sonner';

/**
 * Standard Arthsavora HTTP Client
 * Automatically propagates Bearer JWT tokens, X-Request-ID correlation IDs,
 * and active X-Workspace-ID tenant context.
 */
export const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Injects Auth, Correlation ID, and Workspace Context
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 1. Inject Bearer JWT Token
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 2. Inject or propagate Correlation ID (X-Request-ID)
    if (config.headers && !config.headers['X-Request-ID']) {
      const requestId = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
      config.headers['X-Request-ID'] = requestId;
    }

    // 3. Inject active Workspace Context (X-Workspace-ID)
    const activeWorkspaceId = localStorage.getItem('active_workspace_id');
    if (activeWorkspaceId && config.headers && !config.headers['X-Workspace-ID']) {
      config.headers['X-Workspace-ID'] = activeWorkspaceId;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Standardized Error Normalization
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const errorData = error.response?.data;
    const message = errorData?.error?.message || errorData?.detail || 'An unexpected error occurred.';

    if (status === 401) {
      localStorage.removeItem('token');
      if (typeof window !== 'undefined' && window.location.pathname !== '/auth') {
        window.location.href = '/auth';
      }
    } else if (status === 403) {
      toast.error(message || 'Access denied: Insufficient permissions for this action.');
    } else if (status === 404) {
      // 404s may be expected or anti-IDOR cloaking
    } else if (status === 422) {
      toast.error(message || 'Validation failed. Please check your inputs.');
    } else if (status === 429) {
      toast.warning(message || 'Rate limit exceeded. Please wait a moment.');
    } else if (status >= 500) {
      toast.error('An unexpected server error occurred. Please try again.');
    }

    return Promise.reject(error);
  }
);

export default api;
