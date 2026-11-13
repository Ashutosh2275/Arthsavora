/**
 * Arthsavora Observability and Error Tracking Foundation
 * Prepares the frontend for Sentry and OpenTelemetry distributed tracing.
 * Enforces strict financial data hygiene: never logs sensitive tokens, credentials, or PAN/Aadhaar details.
 */

export interface ErrorContext {
  componentStack?: string;
  url?: string;
  userId?: string;
  workspaceId?: string;
  extra?: Record<string, unknown>;
}

// Redaction patterns for sensitive financial data
const SENSITIVE_KEYS = [
  'password',
  'token',
  'access_token',
  'refresh_token',
  'secret',
  'pan',
  'aadhaar',
  'card',
  'cvv',
  'account_number',
];

export function sanitizeData(data: Record<string, unknown>): Record<string, unknown> {
  const sanitized: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(data)) {
    if (SENSITIVE_KEYS.some((sensitive) => key.toLowerCase().includes(sensitive))) {
      sanitized[key] = '[REDACTED]';
    } else if (value && typeof value === 'object' && !Array.isArray(value)) {
      sanitized[key] = sanitizeData(value as Record<string, unknown>);
    } else {
      sanitized[key] = value;
    }
  }
  return sanitized;
}

export const logger = {
  info: (message: string, context?: Record<string, unknown>) => {
    const payload = context ? sanitizeData(context) : undefined;
    console.info(`[ARTH-INFO] ${message}`, payload || '');
  },
  warn: (message: string, context?: Record<string, unknown>) => {
    const payload = context ? sanitizeData(context) : undefined;
    console.warn(`[ARTH-WARN] ${message}`, payload || '');
  },
  error: (message: string, error?: unknown, context?: ErrorContext) => {
    const safeContext = context ? { ...context, extra: context.extra ? sanitizeData(context.extra) : undefined } : undefined;
    console.error(`[ARTH-ERROR] ${message}`, error, safeContext || '');
  },
};

export function captureException(error: unknown, context?: ErrorContext): string {
  const errorId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `err-${Date.now()}`;
  logger.error(`Exception captured [${errorId}]`, error, context);
  
  // Future Sentry integration point:
  // if (window.Sentry) {
  //   window.Sentry.captureException(error, { extra: context });
  // }
  
  return errorId;
}
