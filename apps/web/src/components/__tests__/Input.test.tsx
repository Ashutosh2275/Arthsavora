import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Input } from '../ui/input';

describe('Input Component', () => {
  it('renders input with label and associates id correctly', () => {
    render(<Input label="Email Address" id="email-field" placeholder="you@domain.com" />);
    const label = screen.getByText('Email Address');
    const input = screen.getByPlaceholderText('you@domain.com');
    expect(label).toHaveAttribute('for', 'email-field');
    expect(input).toHaveAttribute('id', 'email-field');
  });

  it('handles value changes', () => {
    const handleChange = vi.fn();
    render(<Input placeholder="Search" onChange={handleChange} />);
    const input = screen.getByPlaceholderText('Search');
    fireEvent.change(input, { target: { value: 'Salary' } });
    expect(handleChange).toHaveBeenCalled();
  });

  it('renders error message with alert role and aria-invalid', () => {
    render(<Input label="Amount" error="Amount is required" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    const errorMsg = screen.getByRole('alert');
    expect(errorMsg).toHaveTextContent('Amount is required');
  });

  it('renders helper text when no error exists', () => {
    render(<Input label="GSTIN" helperText="Enter 15-digit GST identification number" />);
    expect(screen.getByText('Enter 15-digit GST identification number')).toBeInTheDocument();
  });

  it('toggles password visibility when isPasswordToggle is enabled', () => {
    render(<Input label="Password" type="password" isPasswordToggle placeholder="Enter secret" />);
    const input = screen.getByPlaceholderText('Enter secret');
    expect(input).toHaveAttribute('type', 'password');

    const toggleButton = screen.getByRole('button', { name: /show password/i });
    fireEvent.click(toggleButton);
    expect(input).toHaveAttribute('type', 'text');

    const hideButton = screen.getByRole('button', { name: /hide password/i });
    fireEvent.click(hideButton);
    expect(input).toHaveAttribute('type', 'password');
  });
});
