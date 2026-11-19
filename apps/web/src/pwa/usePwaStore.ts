import { create } from 'zustand';

export interface PwaState {
  isInstallable: boolean;
  isInstalled: boolean;
  deferredPrompt: any | null;
  isOffline: boolean;
  wasOffline: boolean;
  hasUpdate: boolean;
  registration: ServiceWorkerRegistration | null;
  swVersion: string;

  // Actions
  setDeferredPrompt: (event: any | null) => void;
  promptInstall: () => Promise<'accepted' | 'dismissed' | 'unsupported'>;
  setIsInstalled: (installed: boolean) => void;
  setOfflineStatus: (isOffline: boolean) => void;
  setUpdateAvailable: (registration: ServiceWorkerRegistration) => void;
  applyUpdate: () => void;
  dismissUpdate: () => void;
  clearCaches: () => Promise<void>;
  setSwVersion: (version: string) => void;
}

export const usePwaStore = create<PwaState>((set, get) => ({
  isInstallable: false,
  isInstalled:
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    (window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator as any).standalone === true),
  deferredPrompt: null,
  isOffline: typeof navigator !== 'undefined' ? !navigator.onLine : false,
  wasOffline: false,
  hasUpdate: false,
  registration: null,
  swVersion: '1.0.0',

  setDeferredPrompt: (event) => {
    set({
      deferredPrompt: event,
      isInstallable: !!event,
    });
  },

  promptInstall: async () => {
    const { deferredPrompt } = get();
    if (!deferredPrompt) {
      return 'unsupported';
    }

    try {
      deferredPrompt.prompt();
      const choiceResult = await deferredPrompt.userChoice;
      if (choiceResult.outcome === 'accepted') {
        set({ isInstallable: false, deferredPrompt: null, isInstalled: true });
        return 'accepted';
      } else {
        set({ isInstallable: false, deferredPrompt: null });
        return 'dismissed';
      }
    } catch (err) {
      return 'unsupported';
    }
  },

  setIsInstalled: (installed) => set({ isInstalled: installed, isInstallable: false }),

  setOfflineStatus: (isOffline) => {
    const currentOffline = get().isOffline;
    if (currentOffline && !isOffline) {
      // Transitioned from offline to online
      set({ isOffline: false, wasOffline: true });
      setTimeout(() => set({ wasOffline: false }), 4000);
    } else {
      set({ isOffline });
    }
  },

  setUpdateAvailable: (registration) => set({ hasUpdate: true, registration }),

  applyUpdate: () => {
    const { registration } = get();
    if (registration && registration.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
    set({ hasUpdate: false });
    // Reload page once new service worker takes over
    if (typeof window !== 'undefined' && typeof window.location?.reload === 'function') {
      try {
        window.location.reload();
      } catch {
        // Safe fallback in test environments
      }
    }
  },

  dismissUpdate: () => set({ hasUpdate: false }),

  clearCaches: async () => {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_CACHES' });
    }
    if (typeof caches !== 'undefined') {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    }
  },

  setSwVersion: (version) => set({ swVersion: version }),
}));
