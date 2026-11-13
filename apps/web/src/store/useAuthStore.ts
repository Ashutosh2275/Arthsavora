import { create } from 'zustand';
import api from '@/lib/axios';

interface User {
  id: string;
  email: string;
  full_name: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signup: (fullName: string, email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: typeof window !== 'undefined' ? localStorage.getItem('token') : null,
  isAuthenticated: typeof window !== 'undefined' ? !!localStorage.getItem('token') : false,

  login: async (email: string, password: string) => {
    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const { access_token } = response.data;

      localStorage.setItem('token', access_token);
      set({ token: access_token, isAuthenticated: true });
      return { success: true };
    } catch (error: unknown) {
      console.error('Login error:', error);
      const axiosError = error as { response?: { data?: { detail?: string; error?: { message?: string } } } };
      const detail =
        axiosError.response?.data?.detail ||
        axiosError.response?.data?.error?.message ||
        'Invalid email or password';
      return { success: false, error: detail };
    }
  },

  signup: async (fullName: string, email: string, password: string) => {
    try {
      await api.post('/auth/signup', {
        full_name: fullName,
        email,
        password,
      });
      return { success: true };
    } catch (error: unknown) {
      console.error('Signup error:', error);
      const axiosError = error as { response?: { data?: { detail?: string; error?: { message?: string } } } };
      const detail =
        axiosError.response?.data?.detail ||
        axiosError.response?.data?.error?.message ||
        'Signup failed. Please try again.';
      return { success: false, error: detail };
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null, isAuthenticated: false });
  },
}));

export default useAuthStore;
