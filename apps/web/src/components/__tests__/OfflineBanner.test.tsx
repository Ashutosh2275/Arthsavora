import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { OfflineBanner } from '../pwa/OfflineBanner';
import { usePwaStore } from '@/pwa/usePwaStore';

describe('OfflineBanner Component', () => {
  beforeEach(() => {
    usePwaStore.setState({
      isOffline: false,
      wasOffline: false,
    });
  });

  it('renders nothing when application is fully online and synchronized', () => {
    const { container } = render(<OfflineBanner />);
    expect(container.firstChild).toBeNull();
  });

  it('renders prominent alert banner when offline', () => {
    usePwaStore.setState({ isOffline: true, wasOffline: false });
    render(<OfflineBanner />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Offline Mode:/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Financial transactions and reports require an active, secure connection/i)
    ).toBeInTheDocument();
  });

  it('renders green recovery status banner when connection is restored', () => {
    usePwaStore.setState({ isOffline: false, wasOffline: true });
    render(<OfflineBanner />);

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText(/Network connection restored/i)).toBeInTheDocument();
  });
});
