import { create } from 'zustand';
import api from '../api/axios';

const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('token') || null,
  isAuthenticated: !!localStorage.getItem('token'),

  // Login Action
  login: async (email, password) => {
    try {
      // FastAPI OAuth2 expects form-data, not JSON for the login endpoint
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post('/auth/login', formData);
      const { access_token } = response.data;
      
      localStorage.setItem('token', access_token);
      set({ token: access_token, isAuthenticated: true });
      return { success: true };
    } catch (error) {
      console.error("Login Error:", error);
      return { 
        success: false, 
        error: error.response?.data?.detail || "Invalid email or password" 
      };
    }
  },

  // Signup Action
  signup: async (full_name, email, password) => {
    try {
      await api.post('/auth/signup', { full_name, email, password });
      return { success: true };
    } catch (error) {
      console.error("Signup Error:", error);
      return { 
        success: false, 
        error: error.response?.data?.detail || "Signup failed. Email might be taken." 
      };
    }
  },

  // Logout Action
  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null, isAuthenticated: false });
  }
}));

// THE CRITICAL EXPORT LINE
export default useAuthStore;