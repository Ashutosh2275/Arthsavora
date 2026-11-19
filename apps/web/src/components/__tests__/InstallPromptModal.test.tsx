import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { InstallPromptModal } from '../pwa/InstallPromptModal';
import { usePwaStore } from '@/pwa/usePwaStore';

describe('InstallPromptModal Component', () => {
  beforeEach(() => {
    usePwaStore.setState({
      isInstallable: false,
      isInstalled: false,
      promptInstall: vi.fn().mockResolvedValue('accepted'),
    });
  });

  it('renders nothing when isOpen is false', () => {
    const { container } = render(<InstallPromptModal isOpen={false} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders modal dialog with instructions when opened', () => {
    render(<InstallPromptModal isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByRole('dialog', { name: /Install ARTHSAVORA App/i })).toBeInTheDocument();
    expect(screen.getByText(/Progressive Web Application/i)).toBeInTheDocument();
  });

  it('renders Install Now button when isInstallable is true', () => {
    usePwaStore.setState({ isInstallable: true });
    render(<InstallPromptModal isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByRole('button', { name: /Install Now/i })).toBeInTheDocument();
  });

  it('invokes promptInstall when Install Now button is clicked', async () => {
    const mockPrompt = vi.fn().mockResolvedValue('accepted');
    usePwaStore.setState({ isInstallable: true, promptInstall: mockPrompt });

    render(<InstallPromptModal isOpen={true} onClose={vi.fn()} />);

    const installBtn = screen.getByRole('button', { name: /Install Now/i });
    fireEvent.click(installBtn);
    expect(mockPrompt).toHaveBeenCalled();
  });

  it('calls onClose when close button is clicked', () => {
    const mockClose = vi.fn();
    render(<InstallPromptModal isOpen={true} onClose={mockClose} />);

    const closeBtn = screen.getByRole('button', { name: /Close install dialog/i });
    fireEvent.click(closeBtn);
    expect(mockClose).toHaveBeenCalled();
  });
});
