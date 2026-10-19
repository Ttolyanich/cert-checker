import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const ThemeContext = createContext();

export const PALETTES = [
  {
    id: 'classic',
    name: 'Classic Zinc',
    nameRu: 'Классический',
    colors: ['#141416', '#e4e4e7'],
    accent: '#e4e4e7'
  },
  {
    id: 'cyber_lime',
    name: 'Cyber Lime',
    nameRu: 'Кислотно-зеленый',
    colors: ['#0a0a0a', '#b6ff00'],
    accent: '#b6ff00'
  },
  {
    id: 'electric_blue',
    name: 'Electric Blue',
    nameRu: 'Электрический синий',
    colors: ['#101a46', '#245bff'],
    accent: '#245bff'
  },
  {
    id: 'crimson',
    name: 'Crimson Red',
    nameRu: 'Кроваво-красный',
    colors: ['#080808', '#c1121f'],
    accent: '#c1121f'
  },
  {
    id: 'rust_orange',
    name: 'Rust Orange',
    nameRu: 'Ржаво-оранжевый',
    colors: ['#24150f', '#d96b27'],
    accent: '#d96b27'
  },
  {
    id: 'graphite_pink',
    name: 'Graphite Pink',
    nameRu: 'Графитово-розовый',
    colors: ['#292929', '#c88e9b'],
    accent: '#c88e9b'
  }
];

// Compatibility export
export const THEMES = PALETTES;

export function ThemeProvider({ children }) {
  // 1. Theme mode: 'dark' or 'light'
  const [theme, setThemeState] = useState(() => {
    const saved = localStorage.getItem('cert-checker-theme');
    if (saved === 'light' || saved === 'dark') return saved;
    if (saved === 'navy') return 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  });

  // 2. Color palette: 'classic', 'cyber_lime', etc.
  const [palette, setPaletteState] = useState(() => {
    return localStorage.getItem('cert-checker-palette') || 'classic';
  });

  const setTheme = useCallback((newTheme) => {
    const normalized = newTheme === 'light' ? 'light' : 'dark';
    setThemeState(normalized);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState(prev => (prev === 'light' ? 'dark' : 'light'));
  }, []);

  const setPalette = useCallback((newPalette) => {
    setPaletteState(newPalette);
  }, []);

  useEffect(() => {
    // Apply theme mode class
    if (theme === 'light') {
      document.documentElement.classList.add('light-theme');
      document.documentElement.setAttribute('data-theme', 'light');
    } else {
      document.documentElement.classList.remove('light-theme');
      document.documentElement.setAttribute('data-theme', 'dark');
    }
    localStorage.setItem('cert-checker-theme', theme);
  }, [theme]);

  useEffect(() => {
    // Apply data-palette attribute
    document.documentElement.setAttribute('data-palette', palette);
    localStorage.setItem('cert-checker-palette', palette);
  }, [palette]);

  return (
    <ThemeContext.Provider value={{
      theme,
      setTheme,
      toggleTheme,
      palette,
      setPalette,
      palettes: PALETTES,
      themes: PALETTES
    }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
