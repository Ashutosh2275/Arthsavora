import React, { type ReactNode } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Auth from '@/pages/Auth';
import Dashboard from '@/pages/Dashboard';
import Accounts from '@/pages/Accounts';
import Transactions from '@/pages/Transactions';
import { Ledger } from '@/pages/Ledger';
import { Import } from '@/pages/Import';
import Categories from '@/pages/Categories';
import Expenses from '@/pages/Expenses';
import Budget from '@/pages/Budget';
import Goals from '@/pages/Goals';
import Reports from '@/pages/Reports';
import AppLayout from '@/components/layout/AppLayout';
import { ErrorBoundary } from '@/components/feedback/ErrorBoundary';
import useAuthStore from '@/store/useAuthStore';

interface ProtectedRouteProps {
  children: ReactNode;
}

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated ? <>{children}</> : <Navigate to="/auth" replace />;
};

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/auth" element={<Auth />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Dashboard />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/accounts"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Accounts />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/transactions"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Transactions />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/ledger"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Ledger />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/import"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Import />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/categories"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Categories />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/expenses"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Expenses />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/budget"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Budget />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/goals"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Goals />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/reports"
          element={
            <ProtectedRoute>
              <AppLayout>
                <Reports />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </ErrorBoundary>
  );
}
