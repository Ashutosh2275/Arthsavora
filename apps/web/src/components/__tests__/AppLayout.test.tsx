import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { AppLayout } from '../layout/AppLayout';
import useAuthStore from '@/store/useAuthStore';
import { useNotificationStore } from '@/store/useNotificationStore';
import useWorkspaceStore from '@/store/useWorkspaceStore';
import { useThemeStore } from '@/store/useThemeStore';

vi.mock('@/store/useAuthStore');
vi.mock('@/store/useNotificationStore');
vi.mock('@/store/useWorkspaceStore');
vi.mock('@/store/useThemeStore');
vi.mock('@/components/AIChatbot', () => ({
  default: () => <div data-testid="mock-chatbot" />,
}));
vi.mock('../layout/WorkspaceSwitcher', () => ({
  default: () => <div data-testid="mock-workspace-switcher" />,
}));
vi.mock('../layout/GlobalSearch', () => ({
  default: () => <div data-testid="mock-global-search" />,
}));
vi.mock('../ui/ThemeToggle', () => ({
  default: () => <div data-testid="mock-theme-toggle" />,
}));

describe('AppLayout Component', () => {
  const mockLogout = vi.fn();
  const mockFetchUnreadCount = vi.fn();
  const mockFetchWorkspaces = vi.fn();
  const mockInitTheme = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      user: { full_name: 'Ashutosh Sharma', email: 'ashutosh@example.com' },
      logout: mockLogout,
    });
    (useNotificationStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      unreadCount: 3,
      fetchUnreadCount: mockFetchUnreadCount,
    });
    (useWorkspaceStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      activeWorkspace: { id: 'ws-1', name: 'Personal Vault', type: 'personal' },
      fetchWorkspaces: mockFetchWorkspaces,
    });
    (useThemeStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      theme: 'dark',
      initTheme: mockInitTheme,
    });
  });

  it('renders brand identity, accessibility skip link, and main navigation', () => {
    render(
      <BrowserRouter>
        <AppLayout>
          <div>Dashboard Test Content</div>
        </AppLayout>
      </BrowserRouter>
    );

    expect(screen.getByText('Skip to main content')).toBeInTheDocument();
    expect(screen.getByText('ARTHSAVORA')).toBeInTheDocument();
    expect(screen.getByText('Dashboard Test Content')).toBeInTheDocument();
    expect(mockInitTheme).toHaveBeenCalled();
    expect(mockFetchWorkspaces).toHaveBeenCalled();
  });

  it('renders topbar utility controls (global search, workspace switcher, notification badge)', () => {
    render(
      <BrowserRouter>
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      </BrowserRouter>
    );

    expect(screen.getByTestId('mock-workspace-switcher')).toBeInTheDocument();
    expect(screen.getByTestId('mock-global-search')).toBeInTheDocument();
    expect(screen.getByLabelText(/view notifications/i)).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('opens and closes mobile navigation menu drawer', () => {
    render(
      <BrowserRouter>
        <AppLayout>
          <div>Content</div>
        </AppLayout>
      </BrowserRouter>
    );

    const mobileMenuButton = screen.getByLabelText(/open mobile navigation menu/i);
    fireEvent.click(mobileMenuButton);

    expect(screen.getByRole('dialog', { name: /mobile navigation menu/i })).toBeInTheDocument();

    const closeButton = screen.getByLabelText(/close navigation menu/i);
    fireEvent.click(closeButton);

    expect(screen.queryByRole('dialog', { name: /mobile navigation menu/i })).not.toBeInTheDocument();
  });
});
