import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

export const THEMES = [
  {
    id: 'navy',
    name: 'Deep Space',
    accent: '#00d4ff',
    bg: '#0a0e1a',
    preview: ['#0a0e1a', '#00d4ff', '#0d1526'],
  },
  {
    id: 'light',
    name: 'Light',
    accent: '#3b82f6',
    bg: '#f8fafc',
    preview: ['#f8fafc', '#3b82f6', '#e2e8f0'],
  },
];

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('cert-checker-theme') || 'navy';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('cert-checker-theme', theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, themes: THEMES }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
