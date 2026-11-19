import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WorkspaceSwitcher } from '../layout/WorkspaceSwitcher';
import useWorkspaceStore from '@/store/useWorkspaceStore';

vi.mock('@/store/useWorkspaceStore');

const mockWorkspaces = [
  {
    id: 'ws-1',
    name: 'Personal Vault',
    slug: 'personal-vault',
    type: 'personal',
    owner_id: 'user-1',
    currency: 'INR',
    timezone: 'Asia/Kolkata',
    country: 'IN',
    status: 'active',
    settings: {},
    created_at: '2026-04-01T00:00:00Z',
  },
  {
    id: 'ws-2',
    name: 'Sharma Household',
    slug: 'sharma-household',
    type: 'family',
    owner_id: 'user-1',
    currency: 'INR',
    timezone: 'Asia/Kolkata',
    country: 'IN',
    status: 'active',
    settings: {},
    created_at: '2026-04-01T00:00:00Z',
  },
  {
    id: 'ws-3',
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
  },
];

describe('WorkspaceSwitcher Component', () => {
  const mockFetchWorkspaces = vi.fn();
  const mockSwitchWorkspace = vi.fn();
  const mockCreateWorkspace = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useWorkspaceStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      workspaces: mockWorkspaces,
      activeWorkspace: mockWorkspaces[0],
      fetchWorkspaces: mockFetchWorkspaces,
      switchWorkspace: mockSwitchWorkspace,
      createWorkspace: mockCreateWorkspace,
    });
  });

  it('renders the active workspace title and tenancy badge', () => {
    render(<WorkspaceSwitcher />);
    expect(screen.getByText('Personal Vault')).toBeInTheDocument();
    expect(screen.getByText('personal')).toBeInTheDocument();
    expect(mockFetchWorkspaces).toHaveBeenCalled();
  });

  it('opens the dropdown list when clicked and shows available workspaces', () => {
    render(<WorkspaceSwitcher />);
    const trigger = screen.getByRole('button', { name: /select workspace/i });
    fireEvent.click(trigger);

    expect(screen.getByText('Your Workspaces')).toBeInTheDocument();
    expect(screen.getByText('Sharma Household')).toBeInTheDocument();
    expect(screen.getByText('Apex Studio LLP')).toBeInTheDocument();
  });

  it('triggers workspace switch when an item is selected', async () => {
    render(<WorkspaceSwitcher />);
    const trigger = screen.getByRole('button', { name: /select workspace/i });
    fireEvent.click(trigger);

    const familyOption = screen.getByText('Sharma Household');
    fireEvent.click(familyOption);

    expect(mockSwitchWorkspace).toHaveBeenCalledWith('ws-2');
  });

  it('opens the Create Workspace modal when clicking create action', () => {
    render(<WorkspaceSwitcher />);
    const trigger = screen.getByRole('button', { name: /select workspace/i });
    fireEvent.click(trigger);

    const createBtn = screen.getByRole('button', { name: /create new workspace/i });
    fireEvent.click(createBtn);

    expect(screen.getByRole('dialog', { name: /create workspace/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\. Apex Studio LLP, Sharma Household/i)).toBeInTheDocument();
  });
});
