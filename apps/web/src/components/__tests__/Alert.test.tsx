import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Alert } from '../ui/alert';

describe('Alert Component', () => {
  it('renders alert with title and children', () => {
    render(
      <Alert variant="warning" title="GST Audit Notice">
        Quarterly return filing deadline is approaching.
      </Alert>
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('GST Audit Notice')).toBeInTheDocument();
    expect(screen.getByText('Quarterly return filing deadline is approaching.')).toBeInTheDocument();
  });

  it('triggers onDismiss when close button is clicked', () => {
    const handleDismiss = vi.fn();
    render(
      <Alert variant="error" onDismiss={handleDismiss}>
        Payment failed. Please retry.
      </Alert>
    );
    const dismissBtn = screen.getByRole('button', { name: /dismiss alert/i });
    fireEvent.click(dismissBtn);
    expect(handleDismiss).toHaveBeenCalledTimes(1);
  });
});
