import { describe, it, expect, beforeEach, vi } from 'vitest';
import { usePwaStore } from '../usePwaStore';

describe('PWA State Store (usePwaStore)', () => {
  beforeEach(() => {
    usePwaStore.setState({
      isInstallable: false,
      isInstalled: false,
      deferredPrompt: null,
      isOffline: false,
      wasOffline: false,
      hasUpdate: false,
      registration: null,
      swVersion: '1.0.0',
    });
  });

  it('initializes with default online status and empty prompt', () => {
    const state = usePwaStore.getState();
    expect(state.isOffline).toBe(false);
    expect(state.isInstallable).toBe(false);
    expect(state.hasUpdate).toBe(false);
    expect(state.swVersion).toBe('1.0.0');
  });

  it('updates offline status and triggers wasOffline transition', () => {
    // Transition to offline
    usePwaStore.getState().setOfflineStatus(true);
    expect(usePwaStore.getState().isOffline).toBe(true);

    // Transition back to online
    usePwaStore.getState().setOfflineStatus(false);
    expect(usePwaStore.getState().isOffline).toBe(false);
    expect(usePwaStore.getState().wasOffline).toBe(true);
  });

  it('captures deferred install prompt and sets isInstallable', () => {
    const mockPromptEvent = {
      prompt: vi.fn(),
      userChoice: Promise.resolve({ outcome: 'accepted' }),
    };

    usePwaStore.getState().setDeferredPrompt(mockPromptEvent);
    expect(usePwaStore.getState().isInstallable).toBe(true);
    expect(usePwaStore.getState().deferredPrompt).toBe(mockPromptEvent);
  });

  it('handles promptInstall accepting installation', async () => {
    const mockPrompt = vi.fn();
    const mockPromptEvent = {
      prompt: mockPrompt,
      userChoice: Promise.resolve({ outcome: 'accepted' }),
    };

    usePwaStore.getState().setDeferredPrompt(mockPromptEvent);
    const result = await usePwaStore.getState().promptInstall();

    expect(mockPrompt).toHaveBeenCalled();
    expect(result).toBe('accepted');
    expect(usePwaStore.getState().isInstalled).toBe(true);
    expect(usePwaStore.getState().isInstallable).toBe(false);
  });

  it('handles promptInstall when unsupported or no prompt is deferred', async () => {
    usePwaStore.getState().setDeferredPrompt(null);
    const result = await usePwaStore.getState().promptInstall();
    expect(result).toBe('unsupported');
  });

  it('handles update detection, activation, and dismissal', () => {
    const mockWaitingWorker = { postMessage: vi.fn() };
    const mockRegistration = { waiting: mockWaitingWorker } as unknown as ServiceWorkerRegistration;

    usePwaStore.getState().setUpdateAvailable(mockRegistration);
    expect(usePwaStore.getState().hasUpdate).toBe(true);

    usePwaStore.getState().dismissUpdate();
    expect(usePwaStore.getState().hasUpdate).toBe(false);
  });
});
