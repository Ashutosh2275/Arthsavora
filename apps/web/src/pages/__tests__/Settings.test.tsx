import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Settings } from '../Settings';
import useAuthStore from '@/store/useAuthStore';
import useWorkspaceStore from '@/store/useWorkspaceStore';

vi.mock('@/store/useAuthStore');
vi.mock('@/store/useWorkspaceStore');
vi.mock('@/components/ui/ThemeToggle', () => ({
  default: () => <div data-testid="mock-theme-toggle" />,
}));

const mockWorkspace = {
  id: 'ws-1',
  name: 'Apex Studio LLP',
  slug: 'apex-studio-llp',
  type: 'business',
  owner_id: 'user-1',
  currency: 'INR',
  timezone: 'Asia/Kolkata',
  country: 'IN',
  status: 'active',
  settings: {},
  created_at: '2026-04-01T00:00:00Z',
};

const mockMembers = [
  {
    id: 'mem-1',
    workspace_id: 'ws-1',
    user_id: 'user-1',
    full_name: 'Ashutosh Sharma',
    email: 'ashutosh@example.com',
    role: 'owner',
    status: 'active',
    joined_at: '2026-04-01T00:00:00Z',
  },
  {
    id: 'mem-2',
    workspace_id: 'ws-1',
    user_id: 'user-2',
    full_name: 'Priya Patel',
    email: 'priya@example.com',
    role: 'accountant',
    status: 'active',
    joined_at: '2026-04-02T00:00:00Z',
  },
];

describe('Settings Page Component', () => {
  const mockFetchMembers = vi.fn();
  const mockInviteMember = vi.fn();
  const mockRemoveMember = vi.fn();
  const mockUpdateWorkspace = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      user: { full_name: 'Ashutosh Sharma', email: 'ashutosh@example.com' },
    });
    (useWorkspaceStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      activeWorkspace: mockWorkspace,
      members: mockMembers,
      fetchMembers: mockFetchMembers,
      inviteMember: mockInviteMember,
      removeMember: mockRemoveMember,
      updateWorkspace: mockUpdateWorkspace,
    });
  });

  it('renders page header and user profile form by default', () => {
    render(<Settings />);
    expect(screen.getByRole('heading', { name: /Settings & Workspace Management/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue('Ashutosh Sharma')).toBeInTheDocument();
    expect(screen.getByDisplayValue('ashutosh@example.com')).toBeInTheDocument();
  });

  it('switches to Workspace Configuration tab and displays workspace parameters', () => {
    render(<Settings />);
    const wsTab = screen.getByRole('button', { name: /Workspace Configuration/i });
    fireEvent.click(wsTab);

    expect(screen.getByDisplayValue('Apex Studio LLP')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Update Workspace/i })).toBeInTheDocument();
  });

  it('switches to Members tab and displays active members with role badges', () => {
    render(<Settings />);
    const memTab = screen.getByRole('button', { name: /Members & Access Control/i });
    fireEvent.click(memTab);

    expect(screen.getByText('Active Workspace Members')).toBeInTheDocument();
    expect(screen.getByText('Priya Patel')).toBeInTheDocument();
    expect(screen.getByText('priya@example.com')).toBeInTheDocument();
    expect(screen.getByText('accountant')).toBeInTheDocument();
  });

  it('opens invite collaborator modal on Members tab', () => {
    render(<Settings />);
    const memTab = screen.getByRole('button', { name: /Members & Access Control/i });
    fireEvent.click(memTab);

    const inviteBtn = screen.getByRole('button', { name: /Invite Member/i });
    fireEvent.click(inviteBtn);

    expect(screen.getByRole('dialog', { name: /Invite Collaborator/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText('collaborator@example.com')).toBeInTheDocument();
  });

  it('switches to Preferences tab and renders theme and security settings', () => {
    render(<Settings />);
    const prefTab = screen.getByRole('button', { name: /Preferences & Appearance/i });
    fireEvent.click(prefTab);

    expect(screen.getByText('Visual Interface Theme')).toBeInTheDocument();
    expect(screen.getByTestId('mock-theme-toggle')).toBeInTheDocument();
    expect(screen.getByText(/Statutory Financial Recordkeeping Notice/i)).toBeInTheDocument();
  });
});
