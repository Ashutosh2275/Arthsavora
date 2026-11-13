/**
 * Arthsavora Financial & Presentation Utilities
 */

/**
 * Formats a numeric or string monetary value as Indian Rupee (INR)
 * Example: 125000 -> "₹1,25,000.00"
 */
export function formatINR(
  amount: number | string | null | undefined,
  options?: { showFraction?: boolean }
): string {
  if (amount === null || amount === undefined || isNaN(Number(amount))) {
    return '₹0.00';
  }

  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  const showFraction = options?.showFraction ?? true;

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: showFraction ? 2 : 0,
    maximumFractionDigits: 2,
  }).format(num);
}

/**
 * Converts standard Rupee value to exact integer paise
 * Example: 15.50 -> 1550
 */
export function rupeesToPaise(rupees: number | string): number {
  const val = typeof rupees === 'string' ? parseFloat(rupees) : rupees;
  return Math.round(val * 100);
}

/**
 * Converts integer paise to standard decimal Rupee number
 * Example: 1550 -> 15.50
 */
export function paiseToRupees(paise: number): number {
  return paise / 100;
}

/**
 * Formats an ISO date string into Indian standard date format (DD/MM/YYYY)
 */
export function formatDateINR(dateString: string | Date | null | undefined): string {
  if (!dateString) return '—';
  const d = typeof dateString === 'string' ? new Date(dateString) : dateString;
  if (isNaN(d.getTime())) return '—';

  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(d);
}
