import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { UpdatePrompt } from '../pwa/UpdatePrompt';
import { usePwaStore } from '@/pwa/usePwaStore';

describe('UpdatePrompt Component', () => {
  beforeEach(() => {
    usePwaStore.setState({
      hasUpdate: false,
      applyUpdate: vi.fn(),
      dismissUpdate: vi.fn(),
    });
  });

  it('renders nothing when hasUpdate is false', () => {
    const { container } = render(<UpdatePrompt />);
    expect(container.firstChild).toBeNull();
  });

  it('renders update prompt card when hasUpdate is true', () => {
    usePwaStore.setState({ hasUpdate: true });
    render(<UpdatePrompt />);

    expect(screen.getByRole('region', { name: /Application Update Notice/i })).toBeInTheDocument();
    expect(screen.getByText('Update Available')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Update Now/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Later/i })).toBeInTheDocument();
  });

  it('triggers applyUpdate when Update Now button is clicked', () => {
    const mockApply = vi.fn();
    usePwaStore.setState({ hasUpdate: true, applyUpdate: mockApply });
    render(<UpdatePrompt />);

    const updateBtn = screen.getByRole('button', { name: /Update Now/i });
    fireEvent.click(updateBtn);
    expect(mockApply).toHaveBeenCalled();
  });

  it('triggers dismissUpdate when Later button is clicked', () => {
    const mockDismiss = vi.fn();
    usePwaStore.setState({ hasUpdate: true, dismissUpdate: mockDismiss });
    render(<UpdatePrompt />);

    const laterBtn = screen.getByRole('button', { name: /Later/i });
    fireEvent.click(laterBtn);
    expect(mockDismiss).toHaveBeenCalled();
  });
});
