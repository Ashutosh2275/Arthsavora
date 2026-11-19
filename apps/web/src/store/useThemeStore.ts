import { create } from 'zustand';

export type Theme = 'light' | 'dark' | 'system';

interface ThemeState {
  theme: Theme;
  effectiveTheme: 'light' | 'dark';
  setTheme: (theme: Theme) => void;
  initTheme: () => void;
}

const getSystemTheme = (): 'light' | 'dark' => {
  if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
};

const applyThemeToDOM = (effectiveTheme: 'light' | 'dark') => {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  if (effectiveTheme === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
};

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: 'dark',
  effectiveTheme: 'dark',

  setTheme: (theme: Theme) => {
    const effectiveTheme = theme === 'system' ? getSystemTheme() : theme;
    if (typeof window !== 'undefined') {
      localStorage.setItem('arth_theme', theme);
    }
    applyThemeToDOM(effectiveTheme);
    set({ theme, effectiveTheme });
  },

  initTheme: () => {
    if (typeof window === 'undefined') return;
    const stored = (localStorage.getItem('arth_theme') as Theme) || 'dark';
    const effectiveTheme = stored === 'system' ? getSystemTheme() : stored;
    applyThemeToDOM(effectiveTheme);
    set({ theme: stored, effectiveTheme });

    // Listen for system theme changes if system theme is selected
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const listener = (e: MediaQueryListEvent) => {
        if (get().theme === 'system') {
          const newEffective = e.matches ? 'dark' : 'light';
          applyThemeToDOM(newEffective);
          set({ effectiveTheme: newEffective });
        }
      };
      mediaQuery.addEventListener('change', listener);
    }
  },
}));
