import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import PaletteDropdown from '../components/PaletteDropdown';
import { Shield, Sun, Moon, Globe, KeyRound } from 'lucide-react';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [authConfig, setAuthConfig] = useState({ ldap_enabled: false, ldap_domain: null });

  const { login } = useAuth();
  const { t, lang, toggleLanguage } = useLanguage();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    fetch('/api/v1/auth/config')
      .then(res => res.json())
      .then(data => {
        if (data) setAuthConfig(data);
      })
      .catch(() => {});
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      await login(username, password);
    } catch (err) {
      setError(t('login_failed') || 'Invalid credentials');
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="card auth-card">
        <div className="auth-header">
          <div className="auth-logo">
            <Shield size={32} />
          </div>
          <h2>{t('login_title')}</h2>
          <p className="site-meta" style={{ marginTop: '4px' }}>
            {authConfig.ldap_enabled 
              ? (lang === 'ru' ? 'Вход по локальной учетной записи или Active Directory' : 'Local account or Active Directory domain login')
              : t('login_subtitle')}
          </p>
        </div>

        {error && (
          <div className="badge error" style={{ width: '100%', padding: '10px', marginBottom: '20px', borderRadius: 'var(--radius-sm)' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">{t('email_label')}</label>
            <input
              type="text"
              className="form-control"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              placeholder={authConfig.ldap_enabled ? (authConfig.ldap_domain ? `admin или user@${authConfig.ldap_domain}` : 'admin или domain\\user') : 'admin'}
            />
          </div>

          <div className="form-group">
            <label className="form-label">{t('password_label')}</label>
            <input
              type="password"
              className="form-control"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '8px', padding: '12px' }}
            disabled={submitting}
          >
            {submitting ? t('loading') : t('btn_login')}
          </button>
        </form>

        {authConfig.ldap_enabled && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginTop: '16px',
            padding: '8px 12px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            fontSize: '0.8rem',
            color: 'var(--text-secondary)'
          }}>
            <KeyRound size={15} style={{ color: 'var(--accent-color)', flexShrink: 0 }} />
            <span>
              {lang === 'ru' 
                ? 'Поддерживается сквозная доменная авторизация Active Directory' 
                : 'Active Directory domain authentication supported'}
            </span>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '24px', paddingTop: '20px', borderTop: '1px solid var(--border-color)' }}>
          <button className="btn-icon" onClick={toggleLanguage} title="Switch Language">
            <Globe size={18} />
            <span style={{ fontSize: '0.75rem', fontWeight: 'bold', marginLeft: '4px' }}>
              {lang.toUpperCase()}
            </span>
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <PaletteDropdown />
            <button className="btn-icon" onClick={toggleTheme} title="Toggle Dark/Light">
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
