import React, { useState, useRef, useEffect } from 'react';
import { useTheme } from '../context/ThemeContext';
import { useLanguage } from '../context/LanguageContext';
import { Palette, Check } from 'lucide-react';

export default function PaletteDropdown() {
  const { palette, setPalette, palettes } = useTheme();
  const { lang } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="palette-picker-container" ref={dropdownRef} style={{ position: 'relative' }}>
      <button 
        type="button"
        className="btn-icon" 
        onClick={() => setIsOpen(prev => !prev)}
        title={lang === 'ru' ? 'Выбрать цветовую тему' : 'Select Color Palette'}
        style={{ width: '36px', height: '36px' }}
      >
        <Palette size={18} />
      </button>

      {isOpen && (
        <div className="palette-menu" style={{
          position: 'absolute',
          top: 'calc(100% + 8px)',
          right: 0,
          width: '210px',
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-lg)',
          padding: '8px',
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <div style={{
            fontSize: '11px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-muted)',
            padding: '4px 8px 6px 8px',
            borderBottom: '1px solid var(--border-color)',
            marginBottom: '4px'
          }}>
            {lang === 'ru' ? 'Цветовые палитры' : 'Color Palettes'}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            {palettes.map((p) => {
              const isActive = palette === p.id;
              const bgGradient = `linear-gradient(135deg, ${p.colors[0]} 50%, ${p.colors[1]} 50%)`;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => {
                    setPalette(p.id);
                    setIsOpen(false);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    width: '100%',
                    padding: '7px 10px',
                    borderRadius: 'var(--radius-sm)',
                    border: isActive ? '1px solid var(--accent-color)' : '1px solid transparent',
                    background: isActive ? 'var(--bg-surface)' : 'transparent',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    fontSize: '13px',
                    fontWeight: isActive ? 600 : 400,
                    textAlign: 'left',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'var(--bg-input)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <span style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '50%',
                    background: bgGradient,
                    flexShrink: 0,
                    boxShadow: '0 0 0 1px rgba(255,255,255,0.15)'
                  }} />
                  <span style={{ flexGrow: 1 }}>{lang === 'ru' ? p.nameRu : p.name}</span>
                  {isActive && <Check size={14} style={{ color: 'var(--accent-color)' }} />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
