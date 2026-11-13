/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Backwards compatibility
        primary: "#0f172a",
        accent: "#6366f1",

        // Institutional Design Token integration
        arth: {
          bg: {
            base: 'rgb(var(--bg-base) / <alpha-value>)',
            surface: 'rgb(var(--bg-surface) / <alpha-value>)',
            subtle: 'rgb(var(--bg-surface-subtle) / <alpha-value>)',
            elevated: 'rgb(var(--bg-elevated) / <alpha-value>)',
            card: 'rgb(var(--bg-card) / <alpha-value>)',
            input: 'rgb(var(--bg-input) / <alpha-value>)',
          },
          text: {
            primary: 'rgb(var(--text-primary) / <alpha-value>)',
            secondary: 'rgb(var(--text-secondary) / <alpha-value>)',
            muted: 'rgb(var(--text-muted) / <alpha-value>)',
            inverse: 'rgb(var(--text-inverse) / <alpha-value>)',
          },
          brand: {
            primary: 'rgb(var(--brand-primary) / <alpha-value>)',
            hover: 'rgb(var(--brand-hover) / <alpha-value>)',
            accent: 'rgb(var(--brand-accent) / <alpha-value>)',
          },
          border: {
            subtle: 'rgb(var(--border-subtle) / <alpha-value>)',
            default: 'rgb(var(--border-default) / <alpha-value>)',
            focus: 'rgb(var(--border-focus) / <alpha-value>)',
          },
          status: {
            income: 'rgb(var(--status-income) / <alpha-value>)',
            expense: 'rgb(var(--status-expense) / <alpha-value>)',
            warning: 'rgb(var(--status-warning) / <alpha-value>)',
            info: 'rgb(var(--status-info) / <alpha-value>)',
            neutral: 'rgb(var(--status-neutral) / <alpha-value>)',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'SF Mono', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        subtle: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        card: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
        dropdown: '0 10px 15px -3px rgba(0, 0, 0, 0.25)',
        modal: '0 25px 50px -12px rgba(0, 0, 0, 0.45)',
      },
      borderRadius: {
        sm: '6px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        '2xl': '24px',
        '3xl': '32px',
      },
    },
  },
  plugins: [],
}
