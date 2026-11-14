import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Notifications } from '../Notifications';
import { useNotificationStore } from '@/store/useNotificationStore';

vi.mock('@/store/useNotificationStore');

const mockNotifications = [
  {
    id: 'notif-1',
    recipient_user_id: 'user-1',
    workspace_id: 'ws-1',
    category: 'budget',
    event_type: 'budget.threshold_reached',
    title: 'Budget Alert: Dining at 92%',
    message: 'Your Dining budget for November 2026 has reached 92.0% of its allocated limit.',
    severity: 'warning',
    related_resource_type: 'budget',
    related_resource_id: 'bg-1',
    action_url: '/budgets',
    metadata_json: { percentage_spent: 92.0 },
    event_timestamp: '2026-11-14T08:00:00Z',
    created_at: '2026-11-14T08:00:00Z',
    is_read: false,
    read_at: null,
    is_archived: false,
    deliveries: [
      {
        id: 'del-1',
        channel: 'in_app',
        provider: 'internal',
        status: 'delivered',
        attempt_count: 1,
      },
      {
        id: 'del-2',
        channel: 'email',
        provider: 'configured_provider',
        status: 'delivered',
        attempt_count: 1,
      },
    ],
  },
  {
    id: 'notif-2',
    recipient_user_id: 'user-1',
    workspace_id: 'ws-1',
    category: 'recurring',
    event_type: 'recurring.payment_due',
    title: 'Payment Due Today: Netflix (₹649.00)',
    message: 'Expected payment of ₹649.00 for Netflix is scheduled for today.',
    severity: 'warning',
    related_resource_type: 'recurring_occurrence',
    related_resource_id: 'rec-1',
    action_url: '/recurring',
    metadata_json: { amount_paise: 64900 },
    event_timestamp: '2026-11-14T07:30:00Z',
    created_at: '2026-11-14T07:30:00Z',
    is_read: true,
    read_at: '2026-11-14T07:45:00Z',
    is_archived: false,
    deliveries: [],
  },
];

describe('Notifications Page Component', () => {
  let fetchNotificationsMock: any;
  let fetchUnreadCountMock: any;
  let fetchPreferencesMock: any;
  let markAsReadMock: any;
  let markAllAsReadMock: any;
  let archiveNotificationMock: any;
  let deleteNotificationMock: any;
  let setActiveCategoryMock: any;
  let updatePreferenceMock: any;
  let triggerTestNotificationMock: any;
  let clearErrorMock: any;

  beforeEach(() => {
    vi.clearAllMocks();

    fetchNotificationsMock = vi.fn().mockResolvedValue(undefined);
    fetchUnreadCountMock = vi.fn().mockResolvedValue(1);
    fetchPreferencesMock = vi.fn().mockResolvedValue(undefined);
    markAsReadMock = vi.fn().mockResolvedValue(undefined);
    markAllAsReadMock = vi.fn().mockResolvedValue(undefined);
    archiveNotificationMock = vi.fn().mockResolvedValue(undefined);
    deleteNotificationMock = vi.fn().mockResolvedValue(undefined);
    setActiveCategoryMock = vi.fn();
    updatePreferenceMock = vi.fn().mockResolvedValue(undefined);
    triggerTestNotificationMock = vi.fn().mockResolvedValue(undefined);
    clearErrorMock = vi.fn();

    (useNotificationStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      notifications: mockNotifications,
      total: 2,
      unreadCount: 1,
      isLoading: false,
      error: null,
      activeCategory: 'all',
      preferences: [],
      pushSubscriptions: [],
      isPushSupported: true,
      pushPermission: 'default',
      clearError: clearErrorMock,
      setActiveCategory: setActiveCategoryMock,
      fetchNotifications: fetchNotificationsMock,
      fetchUnreadCount: fetchUnreadCountMock,
      markAsRead: markAsReadMock,
      markAllAsRead: markAllAsReadMock,
      archiveNotification: archiveNotificationMock,
      deleteNotification: deleteNotificationMock,
      fetchPreferences: fetchPreferencesMock,
      updatePreference: updatePreferenceMock,
      triggerTestNotification: triggerTestNotificationMock,
    });
  });

  it('renders Notification Center header and action buttons', () => {
    render(<Notifications />);
    expect(screen.getByText('Notification Center')).toBeDefined();
    expect(screen.getByText('Mark all read')).toBeDefined();
    expect(screen.getByText('Test Alert')).toBeDefined();
    expect(fetchNotificationsMock).toHaveBeenCalled();
    expect(fetchUnreadCountMock).toHaveBeenCalled();
  });

  it('renders notifications list with titles and severity badges', () => {
    render(<Notifications />);
    expect(screen.getByText('Budget Alert: Dining at 92%')).toBeDefined();
    expect(screen.getByText('Payment Due Today: Netflix (₹649.00)')).toBeDefined();
    expect(screen.getAllByText('warning').length).toBeGreaterThan(0);
  });

  it('switches category filter tab when clicked', () => {
    render(<Notifications />);
    const budgetTab = screen.getByText('Budgets');
    fireEvent.click(budgetTab);
    expect(setActiveCategoryMock).toHaveBeenCalledWith('budget');
  });

  it('triggers markAsRead when check icon is clicked on unread notification', () => {
    render(<Notifications />);
    const markReadBtn = screen.getByTitle('Mark as read');
    fireEvent.click(markReadBtn);
    expect(markAsReadMock).toHaveBeenCalledWith('notif-1');
  });

  it('triggers markAllAsRead when Mark all read button is clicked', () => {
    render(<Notifications />);
    const markAllBtn = screen.getByText('Mark all read');
    fireEvent.click(markAllBtn);
    expect(markAllAsReadMock).toHaveBeenCalled();
  });

  it('renders Quiet Hours and Timezone Configuration when in settings tab', () => {
    (useNotificationStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      notifications: [],
      total: 0,
      unreadCount: 0,
      isLoading: false,
      error: null,
      activeCategory: 'settings',
      preferences: [],
      pushSubscriptions: [],
      isPushSupported: true,
      pushPermission: 'default',
      clearError: clearErrorMock,
      setActiveCategory: setActiveCategoryMock,
      fetchNotifications: fetchNotificationsMock,
      fetchUnreadCount: fetchUnreadCountMock,
      markAsRead: markAsReadMock,
      markAllAsRead: markAllAsReadMock,
      archiveNotification: archiveNotificationMock,
      deleteNotification: deleteNotificationMock,
      fetchPreferences: fetchPreferencesMock,
      updatePreference: updatePreferenceMock,
      triggerTestNotification: triggerTestNotificationMock,
    });

    render(<Notifications />);
    expect(screen.getByText('Quiet Hours & Timezone Configuration')).toBeDefined();
    expect(screen.getByText('Save Quiet Hours')).toBeDefined();
    expect(screen.getByText('Delivery Channels & Categories')).toBeDefined();
  });
});
