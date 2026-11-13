import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusBadge } from '../ui/status-badge';

describe('StatusBadge Component', () => {
  it('renders status text and icon without relying on color alone', () => {
    render(<StatusBadge status="cleared" />);
    expect(screen.getByText('Cleared')).toBeInTheDocument();
  });

  it('renders pending status with clock icon and amber theme', () => {
    render(<StatusBadge status="pending" />);
    const badge = screen.getByText('Pending').parentElement;
    expect(badge?.className).toContain('text-amber-300');
  });

  it('renders AI prediction tag when isAiPredicted is true', () => {
    render(<StatusBadge status="cleared" isAiPredicted confidenceScore={0.94} />);
    expect(screen.getByText('Cleared')).toBeInTheDocument();
    expect(screen.getByText('AI (94%)')).toBeInTheDocument();
  });
});
