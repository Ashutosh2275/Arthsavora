/**
 * Arthsavora Commercial FinTech Design Tokens
 * Institutional, minimal, accessible, WCAG 2.2 AA compliant design primitives.
 * Supports both Light and Dark themes with strict financial status semantics.
 */

export const colors = {
  // Backgrounds & Surface (Default Dark Theme)
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
    accentHover: '#4f46e5',
  },
  // Semantic Financial Status
  status: {
    income: {
      base: '#10b981',
      hover: '#059669',
      subtle: 'rgba(16, 185, 129, 0.1)',
      border: 'rgba(16, 185, 129, 0.2)',
      text: '#34d399',
    },
    expense: {
      base: '#f43f5e',
      hover: '#e11d48',
      subtle: 'rgba(244, 63, 94, 0.1)',
      border: 'rgba(244, 63, 94, 0.2)',
      text: '#fb7185',
    },
    warning: {
      base: '#f59e0b',
      hover: '#d97706',
      subtle: 'rgba(245, 158, 11, 0.1)',
      border: 'rgba(245, 158, 11, 0.2)',
      text: '#fbbf24',
    },
    info: {
      base: '#0284c7',
      hover: '#0369a1',
      subtle: 'rgba(2, 132, 199, 0.1)',
      border: 'rgba(2, 132, 199, 0.2)',
      text: '#38bdf8',
    },
    neutral: {
      base: '#64748b',
      hover: '#475569',
      subtle: 'rgba(100, 116, 139, 0.1)',
      border: 'rgba(100, 116, 139, 0.2)',
      text: '#94a3b8',
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

export const lightColors = {
  background: {
    base: '#f8fafc',
    surface: '#ffffff',
    surfaceSubtle: '#f1f5f9',
    elevated: '#ffffff',
    card: '#ffffff',
    input: '#ffffff',
  },
  text: {
    primary: '#0f172a',
    secondary: '#475569',
    muted: '#64748b',
    inverse: '#ffffff',
  },
  brand: {
    primary: '#4f46e5',
    primaryHover: '#4338ca',
    primarySubtle: 'rgba(79, 70, 229, 0.08)',
    accent: '#6366f1',
    accentHover: '#4f46e5',
  },
  status: {
    income: {
      base: '#059669',
      hover: '#047857',
      subtle: 'rgba(5, 150, 105, 0.1)',
      border: 'rgba(5, 150, 105, 0.2)',
      text: '#047857',
    },
    expense: {
      base: '#e11d48',
      hover: '#be123c',
      subtle: 'rgba(225, 29, 72, 0.1)',
      border: 'rgba(225, 29, 72, 0.2)',
      text: '#be123c',
    },
    warning: {
      base: '#d97706',
      hover: '#b45309',
      subtle: 'rgba(217, 119, 6, 0.1)',
      border: 'rgba(217, 119, 6, 0.2)',
      text: '#b45309',
    },
    info: {
      base: '#0284c7',
      hover: '#0369a1',
      subtle: 'rgba(2, 132, 199, 0.1)',
      border: 'rgba(2, 132, 199, 0.2)',
      text: '#0369a1',
    },
    neutral: {
      base: '#64748b',
      hover: '#475569',
      subtle: 'rgba(100, 116, 139, 0.1)',
      border: 'rgba(100, 116, 139, 0.2)',
      text: '#475569',
    },
  },
  border: {
    subtle: 'rgba(0, 0, 0, 0.06)',
    default: '#e2e8f0',
    hover: 'rgba(79, 70, 229, 0.3)',
    focus: '#4f46e5',
  },
} as const;

export const spacing = {
  0: '0px',
  0.5: '2px',
  1: '4px',
  1.5: '6px',
  2: '8px',
  2.5: '10px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
  20: '80px',
  24: '96px',
} as const;

export const radii = {
  none: '0px',
  sm: '6px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '24px',
  '3xl': '32px',
  full: '9999px',
} as const;

export const typography = {
  fontFamily: {
    sans: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    mono: '"JetBrains Mono", "SF Mono", Menlo, Consolas, monospace',
  },
  fontFeatures: {
    tabular: '"tnum" 1, "cv05" 1',
  },
  fontSize: {
    xs: ['0.75rem', { lineHeight: '1rem' }],
    sm: ['0.875rem', { lineHeight: '1.25rem' }],
    base: ['1rem', { lineHeight: '1.5rem' }],
    lg: ['1.125rem', { lineHeight: '1.75rem' }],
    xl: ['1.25rem', { lineHeight: '1.75rem' }],
    '2xl': ['1.5rem', { lineHeight: '2rem' }],
    '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
    '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
  },
  fontWeight: {
    regular: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
} as const;

export const shadows = {
  none: 'none',
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
  modal: '0 25px 50px -12px rgba(0, 0, 0, 0.45)',
  dropdown: '0 10px 15px -3px rgba(0, 0, 0, 0.25)',
} as const;

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

export const zIndex = {
  hide: -1,
  base: 0,
  dropdown: 1000,
  sticky: 1100,
  fixed: 1200,
  modalBackdrop: 1300,
  modal: 1400,
  popover: 1500,
  toast: 1600,
  tooltip: 1700,
} as const;

export const motion = {
  durations: {
    fast: '150ms',
    normal: '200ms',
    slow: '300ms',
  },
  easings: {
    default: 'cubic-bezier(0.4, 0, 0.2, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
  },
} as const;

export const components = {
  button: {
    heightSm: '32px',
    heightMd: '40px',
    heightLg: '48px',
  },
  input: {
    heightSm: '32px',
    heightMd: '40px',
    heightLg: '48px',
  },
  layout: {
    headerHeight: '64px',
    sidebarWidthExpanded: '260px',
    sidebarWidthCollapsed: '72px',
    maxContentWidth: '1280px',
  },
} as const;
