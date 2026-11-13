import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { EmptyState } from '../feedback/EmptyState';
import { Button } from '../ui/button';

describe('EmptyState Component', () => {
  it('renders title, description and action', () => {
    render(
      <EmptyState
        title="No Transactions Logged"
        description="Connect your bank account or record your first manual entry."
        action={<Button>Add Transaction</Button>}
      />
    );
    expect(screen.getByText('No Transactions Logged')).toBeInTheDocument();
    expect(
      screen.getByText('Connect your bank account or record your first manual entry.')
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add transaction/i })).toBeInTheDocument();
  });
});
