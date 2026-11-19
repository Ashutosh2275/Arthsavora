import { useState, useEffect, useCallback } from 'react';
import { useNotificationStore } from '@/store/useNotificationStore';

export type PushSupportStatus = 'supported' | 'unsupported' | 'checking';
export type PushPermissionStatus = 'default' | 'granted' | 'denied' | 'unsupported';

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export function useWebPush() {
  const [supportStatus, setSupportStatus] = useState<PushSupportStatus>('checking');
  const [permissionStatus, setPermissionStatus] = useState<PushPermissionStatus>('default');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { registerPushSubscription, revokePushSubscription, pushSubscriptions } =
    useNotificationStore();

  // Check support and current subscription status
  useEffect(() => {
    if (
      typeof window === 'undefined' ||
      !('serviceWorker' in navigator) ||
      !('PushManager' in window) ||
      !('Notification' in window)
    ) {
      setSupportStatus('unsupported');
      setPermissionStatus('unsupported');
      return;
    }

    setSupportStatus('supported');
    setPermissionStatus(Notification.permission as PushPermissionStatus);

    navigator.serviceWorker.ready.then((registration) => {
      registration.pushManager.getSubscription().then((subscription) => {
        setIsSubscribed(!!subscription);
      });
    });
  }, []);

  const subscribeToPush = useCallback(
    async (vapidPublicKey?: string) => {
      if (supportStatus !== 'supported') {
        setError('Push notifications are not supported on this browser or platform.');
        return false;
      }

      setIsLoading(true);
      setError(null);

      try {
        const permission = await Notification.requestPermission();
        setPermissionStatus(permission as PushPermissionStatus);

        if (permission !== 'granted') {
          setIsLoading(false);
          return false;
        }

        const registration = await navigator.serviceWorker.ready;

        // Default public key fallback for dev/demo if not passed
        const applicationServerKey = vapidPublicKey
          ? urlBase64ToUint8Array(vapidPublicKey)
          : undefined;

        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: applicationServerKey as any,
        });

        const p256dhKey = subscription.getKey('p256dh');
        const authKey = subscription.getKey('auth');

        const p256dhBase64 = p256dhKey
          ? btoa(String.fromCharCode.apply(null, Array.from(new Uint8Array(p256dhKey))))
          : '';
        const authBase64 = authKey
          ? btoa(String.fromCharCode.apply(null, Array.from(new Uint8Array(authKey))))
          : '';

        await registerPushSubscription(subscription.endpoint, p256dhBase64, authBase64);

        setIsSubscribed(true);
        setIsLoading(false);
        return true;
      } catch (err: any) {
        setError(err.message || 'Failed to subscribe to web push notifications');
        setIsLoading(false);
        return false;
      }
    },
    [supportStatus, registerPushSubscription]
  );

  const unsubscribeFromPush = useCallback(async () => {
    if (supportStatus !== 'supported') return false;

    setIsLoading(true);
    setError(null);

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (subscription) {
        await subscription.unsubscribe();
        const existing = pushSubscriptions.find((s) => s.endpoint === subscription.endpoint);
        if (existing) {
          await revokePushSubscription(existing.id);
        }
      }

      setIsSubscribed(false);
      setIsLoading(false);
      return true;
    } catch (err: any) {
      setError(err.message || 'Failed to unsubscribe from push notifications');
      setIsLoading(false);
      return false;
    }
  }, [supportStatus, pushSubscriptions, revokePushSubscription]);

  return {
    supportStatus,
    permissionStatus,
    isSubscribed,
    isLoading,
    error,
    subscribeToPush,
    unsubscribeFromPush,
  };
}
