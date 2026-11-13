export const env = {
  apiUrl: import.meta.env.VITE_API_URL || '/api',
  appTitle: import.meta.env.VITE_APP_TITLE || 'ARTHSAVORA',
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
} as const;
