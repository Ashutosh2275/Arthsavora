import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Modal } from '../ui/modal';
import { ConfirmDialog } from '../ui/confirm-dialog';

describe('Modal & ConfirmDialog Components', () => {
  it('does not render when isOpen is false', () => {
    render(
      <Modal isOpen={false} onClose={vi.fn()} title="Test Dialog">
        Modal Content
      </Modal>
    );
    expect(screen.queryByText('Test Dialog')).not.toBeInTheDocument();
  });

  it('renders correctly when isOpen is true', () => {
    render(
      <Modal isOpen={true} onClose={vi.fn()} title="Test Dialog">
        Modal Content
      </Modal>
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Test Dialog')).toBeInTheDocument();
    expect(screen.getByText('Modal Content')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Test Dialog">
        Modal Content
      </Modal>
    );
    const closeBtn = screen.getByRole('button', { name: /close dialog/i });
    fireEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when Escape key is pressed', () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Test Dialog">
        Modal Content
      </Modal>
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('renders ConfirmDialog with confirm and cancel buttons', () => {
    const handleConfirm = vi.fn();
    const handleClose = vi.fn();
    render(
      <ConfirmDialog
        isOpen={true}
        onClose={handleClose}
        onConfirm={handleConfirm}
        title="Delete Expense"
        message="Are you sure you want to delete this transaction?"
        confirmText="Yes, Delete"
      />
    );
    expect(screen.getByText('Delete Expense')).toBeInTheDocument();
    const confirmBtn = screen.getByRole('button', { name: /yes, delete/i });
    fireEvent.click(confirmBtn);
    expect(handleConfirm).toHaveBeenCalledTimes(1);
  });
});
