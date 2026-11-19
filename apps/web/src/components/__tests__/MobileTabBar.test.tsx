import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { MobileTabBar } from '../layout/MobileTabBar';
import { useNotificationStore } from '@/store/useNotificationStore';

describe('MobileTabBar Component', () => {
  it('renders mobile navigation landmarks and primary navigation destinations', () => {
    useNotificationStore.setState({ unreadCount: 3 });

    render(
      <MemoryRouter initialEntries={['/']}>
        <MobileTabBar />
      </MemoryRouter>
    );

    expect(screen.getByRole('navigation', { name: /Mobile Bottom Navigation/i })).toBeInTheDocument();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Accounts')).toBeInTheDocument();
    expect(screen.getByText('Add Tx')).toBeInTheDocument();
    expect(screen.getByText('Scan')).toBeInTheDocument();
    expect(screen.getByText('Alerts')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // Unread notification badge
  });

  it('renders Add Tx center action button with link to new transaction action', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <MobileTabBar />
      </MemoryRouter>
    );

    const addAction = screen.getByRole('link', { name: /Record New Transaction/i });
    expect(addAction).toBeInTheDocument();
    expect(addAction.getAttribute('href')).toBe('/transactions?action=new');
  });
});
