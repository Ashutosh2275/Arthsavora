/**
 * Arthsavora Commercial FinTech Design Tokens
 * Institutional, minimal, accessible, WCAG AAA compliant design primitives.
 */

export const colors = {
  // Backgrounds & Surface
  background: {
    base: '#0b0f1a',
    surface: '#0f172a',
    surfaceSubtle: '#1e293b',
    elevated: '#1e293b',
    card: '#0f172a',
    input: '#020617',
  },
  // Text & Content Hierarchy
  text: {
    primary: '#f8fafc',
    secondary: '#94a3b8',
    muted: '#64748b',
    inverse: '#0b0f1a',
  },
  // Brand & Action
  brand: {
    primary: '#4f46e5',
    primaryHover: '#4338ca',
    primarySubtle: 'rgba(79, 70, 229, 0.1)',
    accent: '#6366f1',
  },
  // Semantic Financial Status
  status: {
    income: {
      base: '#10b981',
      subtle: 'rgba(16, 185, 129, 0.1)',
      border: 'rgba(16, 185, 129, 0.2)',
    },
    expense: {
      base: '#f43f5e',
      subtle: 'rgba(244, 63, 94, 0.1)',
      border: 'rgba(244, 63, 94, 0.2)',
    },
    warning: {
      base: '#f59e0b',
      subtle: 'rgba(245, 158, 11, 0.1)',
      border: 'rgba(245, 158, 11, 0.2)',
    },
    neutral: {
      base: '#64748b',
      subtle: 'rgba(100, 116, 139, 0.1)',
      border: 'rgba(100, 116, 139, 0.2)',
    },
  },
  // Borders
  border: {
    subtle: 'rgba(255, 255, 255, 0.06)',
    default: '#1e293b',
    hover: 'rgba(99, 102, 241, 0.3)',
    focus: '#6366f1',
  },
} as const;

export const spacing = {
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
} as const;

export const radii = {
  sm: '6px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '24px',
  full: '9999px',
} as const;

export const typography = {
  fontFamily: {
    sans: 'Inter, system-ui, -apple-system, sans-serif',
    mono: 'JetBrains Mono, Menlo, monospace',
  },
  fontSize: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '1.875rem',
    '4xl': '2.25rem',
  },
} as const;
