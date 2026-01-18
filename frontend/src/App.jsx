import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Wallet, Target, LogOut, ShieldCheck, Trophy, FileText } from 'lucide-react';
import { useState } from 'react';

import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import Expenses from './pages/Expenses';
import Budget from './pages/Budget';
import Goals from './pages/Goals';
import Reports from './pages/Reports';
import AIChatbot from './components/AIChatbot'; // Import Widget
import useAuthStore from './store/useAuthStore';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated ? children : <Navigate to="/auth" />;
};

const Layout = ({ children }) => {
  const { logout } = useAuthStore();
  const location = useLocation();

  const navItems = [
    { name: 'Analytics', path: '/dashboard', icon: <LayoutDashboard size={18} /> },
    { name: 'Expenses', path: '/expenses', icon: <Wallet size={18} /> },
    { name: 'Budget & AI', path: '/budget', icon: <Target size={18} /> },
    { name: 'Milestones', path: '/goals', icon: <Trophy size={18} /> },
    { name: 'Reports', path: '/reports', icon: <FileText size={18} /> },
  ];

  return (
    <div className="min-h-screen bg-[#0b0f1a] text-white">
      <nav className="bg-slate-900/80 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-20 flex items-center justify-between">
          <div className="flex items-center gap-10">
            <div className="flex items-center gap-2">
              <ShieldCheck className="text-indigo-500" size={24} />
              <span className="font-black tracking-tighter text-xl uppercase">ARTHSAVORA</span>
            </div>
            <div className="hidden md:flex gap-2">
              {navItems.map((item) => (
                <Link key={item.path} to={item.path} className={`px-4 py-2 rounded-2xl text-sm font-bold transition-all ${location.pathname === item.path ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}>
                  {item.name}
                </Link>
              ))}
            </div>
          </div>
          <button onClick={logout} className="text-slate-500 hover:text-red-400 font-bold text-xs uppercase tracking-widest transition-all">
            <LogOut size={16} className="inline mr-2" /> Sign Out
          </button>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
      
      {/* GLOBAL AI CHATBOT */}
      <AIChatbot /> 
    </div>
  );
};

function App() {
  return (
    <Routes>
      <Route path="/auth" element={<Auth />} />
      <Route path="/dashboard" element={<ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>} />
      <Route path="/expenses" element={<ProtectedRoute><Layout><Expenses /></Layout></ProtectedRoute>} />
      <Route path="/budget" element={<ProtectedRoute><Layout><Budget /></Layout></ProtectedRoute>} />
      <Route path="/goals" element={<ProtectedRoute><Layout><Goals /></Layout></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><Layout><Reports /></Layout></ProtectedRoute>} />
      <Route path="/" element={<Navigate to="/dashboard" />} />
      <Route path="*" element={<Navigate to="/dashboard" />} />
    </Routes>
  );
}

export default App;