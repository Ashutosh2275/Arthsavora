import { usePwaStore } from './usePwaStore';

/**
 * Initializes and registers the ARTHSAVORA service worker and network monitoring.
 */
export function initServiceWorker(): () => void {
  if (typeof window === 'undefined') {
    return () => {};
  }

  const { setDeferredPrompt, setIsInstalled, setOfflineStatus, setUpdateAvailable, setSwVersion } =
    usePwaStore.getState();

  // 1. Online / Offline network status listeners
  const handleOnline = () => setOfflineStatus(false);
  const handleOffline = () => setOfflineStatus(true);

  window.addEventListener('online', handleOnline);
  window.addEventListener('offline', handleOffline);

  // 2. Capture PWA installation prompt
  const handleBeforeInstallPrompt = (e: Event) => {
    e.preventDefault();
    setDeferredPrompt(e);
  };

  const handleAppInstalled = () => {
    setIsInstalled(true);
    setDeferredPrompt(null);
  };

  window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
  window.addEventListener('appinstalled', handleAppInstalled);

  // 3. Register Service Worker in supporting browsers
  let registrationRef: ServiceWorkerRegistration | null = null;

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker
      .register('/sw.js', { scope: '/' })
      .then((registration) => {
        registrationRef = registration;

        // Check if there is already an active waiting worker
        if (registration.waiting) {
          setUpdateAvailable(registration);
        }

        // Detect updates in the background
        registration.addEventListener('updatefound', () => {
          const installingWorker = registration.installing;
          if (installingWorker) {
            installingWorker.addEventListener('statechange', () => {
              if (installingWorker.state === 'installed') {
                if (navigator.serviceWorker.controller) {
                  // A new update is ready to be applied
                  setUpdateAvailable(registration);
                }
              }
            });
          }
        });

        // Query SW for active version via message channel
        if (registration.active) {
          const messageChannel = new MessageChannel();
          messageChannel.port1.onmessage = (event) => {
            if (event.data && event.data.version) {
              setSwVersion(event.data.version);
            }
          };
          registration.active.postMessage({ type: 'GET_VERSION' }, [messageChannel.port2]);
        }
      })
      .catch((error) => {
        // Silently capture registration errors without crashing the web app
        console.warn('[PWA] Service worker registration failed or unsupported in this context:', error);
      });

    // Detect controller changes (when new SW activates)
    let refreshing = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!refreshing) {
        refreshing = true;
      }
    });
  }

  // Cleanup handler
  return () => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
    window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.removeEventListener('appinstalled', handleAppInstalled);
  };
}

/**
 * Unregisters the service worker and clears associated caches.
 */
export async function unregisterServiceWorker(): Promise<boolean> {
  if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
    const registration = await navigator.serviceWorker.getRegistration();
    if (registration) {
      await usePwaStore.getState().clearCaches();
      return await registration.unregister();
    }
  }
  return false;
}
