import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Shield, Sun, Moon, Globe, LogOut, RefreshCw, 
  CheckCircle, AlertTriangle, XCircle, HelpCircle, Tv, LogIn
} from 'lucide-react';

const Dashboard = () => {
  const { user, token, logout } = useAuth();
  const { t, lang, toggleLanguage } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch sites list (public GET)
  const fetchSites = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/sites/');
      if (res.ok) {
        const data = await res.json();
        setSites(data);
      }
    } catch (err) {
      console.error('Error fetching sites:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSites();
    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchSites, 60000);
    return () => clearInterval(interval);
  }, [fetchSites]);

  // Helper: Parse date string safely as UTC if it lacks timezone info
  const parseDateSafely = (dateString) => {
    if (!dateString) return null;
    // If it doesn't end with Z and doesn't contain a timezone offset (+ or - after the time part)
    if (!dateString.endsWith('Z') && !/[-+]\d{2}:?\d{2}$/.test(dateString)) {
      return new Date(dateString + 'Z');
    }
    return new Date(dateString);
  };

  // Helper: Calculate remaining days
  const getDaysRemaining = (validTo) => {
    if (!validTo) return null;
    const diffTime = parseDateSafely(validTo) - new Date();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  // Helper: Calculate certificate lifetime progress percentage
  const getLifetimeProgress = (validFrom, validTo) => {
    if (!validFrom || !validTo) return 0;
    const start = parseDateSafely(validFrom).getTime();
    const end = parseDateSafely(validTo).getTime();
    const now = new Date().getTime();
    
    if (now >= end) return 0;
    if (now <= start) return 100;
    
    const total = end - start;
    const remaining = end - now;
    return Math.max(0, Math.min(100, (remaining / total) * 100));
  };

  // Helper: Format date
  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return parseDateSafely(dateString).toLocaleDateString(lang === 'ru' ? 'ru-RU' : 'en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Helper: Format last checked time
  const formatLastChecked = (dateString) => {
    if (!dateString) return t('db_status_unchecked');
    const diffMs = new Date() - parseDateSafely(dateString);
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return t('db_checked_just_now');
    if (diffMins < 60) return t('db_checked_ago', { time: `${diffMins} ${lang === 'ru' ? 'мин.' : 'm.'}` });
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return t('db_checked_ago', { time: `${diffHours} ${lang === 'ru' ? 'ч.' : 'h.'}` });
    
    return formatDate(dateString);
  };

  return (
    <>
      {/* Header */}
      <header className="header">
        <div className="container header-content">
          <div className="logo-area" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
            <Shield size={24} style={{ color: 'var(--accent-color)' }} />
            <span>Cert-Checker</span>
          </div>
          
          <nav className="nav-links">
            <Link to="/" className="nav-link active">{t('nav_dashboard')}</Link>
            {token && <Link to="/admin" className="nav-link">{t('nav_admin')}</Link>}
            <Link to="/tv" className="nav-link" target="_blank">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Tv size={16} /> {t('nav_tv')}
              </span>
            </Link>
          </nav>

          <div className="header-controls">
            {token && <span className="site-meta" style={{ marginRight: '8px' }}>{user?.username}</span>}
            <button className="btn-icon" onClick={toggleLanguage} title="Switch Language">
              <Globe size={18} />
              <span style={{ fontSize: '0.75rem', fontWeight: 'bold', marginLeft: '4px' }}>
                {lang.toUpperCase()}
              </span>
            </button>
            <button className="btn-icon" onClick={toggleTheme} title="Toggle Theme">
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            
            {token ? (
              <button className="btn-icon" onClick={logout} title={t('nav_logout')} style={{ color: 'var(--color-expired)' }}>
                <LogOut size={18} />
              </button>
            ) : (
              <Link to="/login" className="btn btn-primary" style={{ padding: '6px 14px', fontSize: '0.85rem' }}>
                <span>{t('nav_login_btn')}</span>
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container" style={{ flexGrow: 1, padding: '32px 24px' }}>
        
        {/* Title and Refresh */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h2>{t('db_title')}</h2>
          <button className="btn btn-secondary" style={{ padding: '6px 12px' }} onClick={fetchSites} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} style={{ marginRight: '6px' }} />
            {loading ? t('loading') : (lang === 'ru' ? 'Обновить' : 'Refresh')}
          </button>
        </div>

        {/* Dashboard Table */}
        {loading && sites.length === 0 ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '64px' }}>
            <div className="badge warning">{t('loading')}</div>
          </div>
        ) : sites.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '64px', color: 'var(--text-secondary)' }}>
            <HelpCircle size={48} style={{ margin: '0 auto 16px auto', display: 'block', strokeWidth: 1.5 }} />
            <p>{t('db_no_sites')}</p>
          </div>
        ) : (
          <div className="card" style={{ padding: '16px', overflow: 'hidden' }}>
            <div className="table-container" style={{ border: 'none', marginTop: 0 }}>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{t('tb_host')}</th>
                    <th>{t('tb_port')}</th>
                    <th>{t('tb_status')}</th>
                    <th style={{ width: '260px' }}>{t('tb_expiry')}</th>
                    <th>{t('tb_days')}</th>
                    <th>{t('tb_issuer')}</th>
                    <th>{t('tb_checked')}</th>
                  </tr>
                </thead>
                <tbody>
                  {sites.map((site) => {
                    const daysRemaining = getDaysRemaining(site.ssl_valid_to);
                    const progress = getLifetimeProgress(site.ssl_valid_from, site.ssl_valid_to);
                    
                    let statusClass = 'unchecked';
                    let StatusIcon = HelpCircle;
                    let statusText = t('db_status_unchecked');
                    
                    if (site.status === 'valid') {
                      statusClass = 'valid';
                      StatusIcon = CheckCircle;
                      statusText = t('db_status_valid');
                    } else if (site.status === 'warning') {
                      statusClass = 'warning';
                      StatusIcon = AlertTriangle;
                      statusText = t('db_status_warning');
                    } else if (site.status === 'expired') {
                      statusClass = 'expired';
                      StatusIcon = XCircle;
                      statusText = t('db_status_expired');
                    } else if (site.status === 'error') {
                      statusClass = 'error';
                      StatusIcon = XCircle;
                      statusText = t('db_status_error');
                    }

                    return (
                      <tr key={site.id}>
                        <td>
                          <span style={{ fontWeight: '700', fontSize: '1rem' }}>{site.hostname}</span>
                        </td>
                        <td>
                          <code>{site.port}</code>
                        </td>
                        <td>
                          <span className={`badge ${statusClass}`} style={{ fontSize: '0.75rem' }}>
                            <StatusIcon size={12} />
                            {statusText}
                          </span>
                        </td>
                        <td>
                          {site.status !== 'error' && site.ssl_valid_to ? (
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                                <span>{formatDate(site.ssl_valid_from)}</span>
                                <span>{formatDate(site.ssl_valid_to)}</span>
                              </div>
                              <div className="progress-container" style={{ height: '4px', margin: 0 }}>
                                <div 
                                  className={`progress-bar ${daysRemaining <= 0 ? 'expired' : daysRemaining <= site.warning_days ? 'warning' : 'valid'}`} 
                                  style={{ width: `${progress}%` }}
                                />
                              </div>
                            </div>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>—</span>
                          )}
                        </td>
                        <td>
                          {site.status === 'error' ? (
                            <span style={{ color: 'var(--color-expired)', fontSize: '0.85rem', fontWeight: '500' }} title={site.last_error}>
                              {site.last_error?.slice(0, 30) || 'Error'}...
                            </span>
                          ) : daysRemaining !== null ? (
                            <span className={`${daysRemaining <= 0 ? 'expired' : daysRemaining <= site.warning_days ? 'warning' : 'valid'}`} style={{ fontWeight: '800', fontSize: '1.1rem', color: daysRemaining <= 0 ? 'var(--color-expired)' : daysRemaining <= site.warning_days ? 'var(--color-warning)' : 'var(--color-valid)' }}>
                              {Math.abs(daysRemaining)} <span style={{ fontSize: '0.8rem', fontWeight: 'normal', color: 'var(--text-secondary)' }}>
                                {daysRemaining < 0 ? t('db_days_expired') : t('db_days_left')}
                              </span>
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>—</span>
                          )}
                        </td>
                        <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                          {site.ssl_issuer || '—'}
                        </td>
                        <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          {formatLastChecked(site.last_checked)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
      
      {/* Dynamic Rotation Style */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </>
  );
};

export default Dashboard;
