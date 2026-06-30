import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { Shield, Clock, CheckCircle, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';

const TVDashboard = () => {
  const { t, lang } = useLanguage();
  const [sites, setSites] = useState([]);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [loading, setLoading] = useState(true);

  // 1. Clock effect
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // 2. Fetch sites function (public GET)
  const fetchAllSites = async () => {
    try {
      const res = await fetch('/api/v1/sites/');
      if (res.ok) {
        const data = await res.json();
        setSites(data);
      }
    } catch (err) {
      console.error('Error fetching sites for TV Dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllSites();
    // Refresh every 30 seconds
    const interval = setInterval(fetchAllSites, 30000);
    return () => clearInterval(interval);
  }, []);

  const getDaysRemaining = (validTo) => {
    if (!validTo) return null;
    const diffTime = new Date(validTo) - new Date();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  const getLifetimeProgress = (validFrom, validTo) => {
    if (!validFrom || !validTo) return 0;
    const start = new Date(validFrom).getTime();
    const end = new Date(validTo).getTime();
    const now = new Date().getTime();
    
    if (now >= end) return 0;
    if (now <= start) return 100;
    
    const total = end - start;
    const remaining = end - now;
    return Math.max(0, Math.min(100, (remaining / total) * 100));
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString(lang === 'ru' ? 'ru-RU' : 'en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatDate = (date) => {
    return date.toLocaleDateString(lang === 'ru' ? 'ru-RU' : 'en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const formatSimpleDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString(lang === 'ru' ? 'ru-RU' : 'en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Stats
  const expiredCount = sites.filter(s => s.status === 'expired').length;
  const warningCount = sites.filter(s => s.status === 'warning').length;
  const errorCount = sites.filter(s => s.status === 'error').length;
  const totalAlerts = expiredCount + warningCount + errorCount;

  return (
    <div className="tv-layout" style={{ padding: '24px', backgroundColor: '#05070f' }}>
      
      {/* TV Header */}
      <div className="tv-header" style={{ marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Shield size={32} style={{ color: 'var(--accent-color)' }} />
            <h1 className="tv-title" style={{ fontSize: '2.2rem', fontWeight: '900', letterSpacing: '-0.03em' }}>
              {t('tv_title')}
            </h1>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginTop: '6px', fontSize: '1.05rem', fontWeight: '500' }}>
            {sites.length} {lang === 'ru' ? 'сайтов в мониторинге' : 'sites under monitor'}
            {totalAlerts > 0 && (
              <span style={{ color: 'var(--color-expired)', marginLeft: '16px', fontWeight: '700', textShadow: '0 0 10px rgba(239,68,68,0.3)' }}>
                ⚠️ {totalAlerts} {lang === 'ru' ? 'предупреждений' : 'alerts'}
              </span>
            )}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', textAlign: 'right' }}>
          <div>
            <div className="tv-time" style={{ fontSize: '2.2rem', fontWeight: '900', color: '#ffffff', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
              {formatTime(currentTime)}
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '2px', fontWeight: '500' }}>
              {formatDate(currentTime)}
            </div>
          </div>
          <Clock size={32} style={{ color: 'var(--text-secondary)' }} />
        </div>
      </div>

      {/* Fullscreen TV Table */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flexGrow: 1 }}>
          <div className="badge warning" style={{ fontSize: '1.2rem', padding: '12px 24px' }}>
            {t('loading')}
          </div>
        </div>
      ) : (
        <div className="card" style={{ padding: '20px', backgroundColor: 'rgba(11, 15, 25, 0.8)', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <div className="table-container" style={{ overflow: 'hidden' }}>
            <table className="admin-table" style={{ width: '100%' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid rgba(255, 255, 255, 0.08)' }}>
                  <th style={{ fontSize: '0.95rem', padding: '14px 16px', color: 'rgba(255, 255, 255, 0.6)' }}>{t('tb_host')}</th>
                  <th style={{ fontSize: '0.95rem', padding: '14px 16px', color: 'rgba(255, 255, 255, 0.6)', width: '100px' }}>{t('tb_port')}</th>
                  <th style={{ fontSize: '0.95rem', padding: '14px 16px', color: 'rgba(255, 255, 255, 0.6)', width: '150px' }}>{t('tb_status')}</th>
                  <th style={{ fontSize: '0.95rem', padding: '14px 16px', color: 'rgba(255, 255, 255, 0.6)', width: '320px' }}>{t('tb_expiry')}</th>
                  <th style={{ fontSize: '0.95rem', padding: '14px 16px', color: 'rgba(255, 255, 255, 0.6)', width: '220px' }}>{t('tb_days')}</th>
                  <th style={{ fontSize: '0.95rem', padding: '14px 16px', color: 'rgba(255, 255, 255, 0.6)' }}>{t('tb_issuer')}</th>
                </tr>
              </thead>
              <tbody>
                {sites.map((site) => {
                  const daysRemaining = getDaysRemaining(site.ssl_valid_to);
                  const progress = getLifetimeProgress(site.ssl_valid_from, site.ssl_valid_to);
                  
                  let statusClass = 'unchecked';
                  let StatusIcon = HelpCircle;
                  let statusText = t('db_status_unchecked');
                  let glowStyle = {};
                  
                  if (site.status === 'valid') {
                    statusClass = 'valid';
                    StatusIcon = CheckCircle;
                    statusText = t('db_status_valid');
                  } else if (site.status === 'warning') {
                    statusClass = 'warning';
                    StatusIcon = AlertTriangle;
                    statusText = t('db_status_warning');
                    // Pulsing orange row style
                    glowStyle = {
                      backgroundColor: 'rgba(245, 158, 11, 0.03)',
                      boxShadow: 'inset 0 0 10px rgba(245, 158, 11, 0.05)'
                    };
                  } else if (site.status === 'expired') {
                    statusClass = 'expired';
                    StatusIcon = XCircle;
                    statusText = t('db_status_expired');
                    // Pulsing red row style
                    glowStyle = {
                      backgroundColor: 'rgba(239, 68, 68, 0.04)',
                      boxShadow: 'inset 0 0 10px rgba(239, 68, 68, 0.05)'
                    };
                  } else if (site.status === 'error') {
                    statusClass = 'error';
                    StatusIcon = XCircle;
                    statusText = t('db_status_error');
                    glowStyle = {
                      backgroundColor: 'rgba(239, 68, 68, 0.04)'
                    };
                  }

                  return (
                    <tr key={site.id} style={{ ...glowStyle, transition: 'background-color 0.3s' }}>
                      
                      {/* Hostname */}
                      <td style={{ padding: '16px', borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <span style={{ 
                          fontSize: '1.25rem', 
                          fontWeight: '800', 
                          color: '#ffffff',
                          textShadow: site.status === 'expired' || site.status === 'error' ? '0 0 12px rgba(239, 68, 68, 0.3)' : 
                                      site.status === 'warning' ? '0 0 12px rgba(245, 158, 11, 0.3)' : 'none'
                        }}>
                          {site.hostname}
                        </span>
                      </td>

                      {/* Port */}
                      <td style={{ padding: '16px', borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <code style={{ fontSize: '1.1rem', color: 'rgba(255, 255, 255, 0.6)', fontWeight: '600' }}>
                          {site.port}
                        </code>
                      </td>

                      {/* Status */}
                      <td style={{ padding: '16px', borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <span className={`badge ${statusClass}`} style={{ fontSize: '0.85rem', padding: '6px 12px', fontWeight: '700' }}>
                          <StatusIcon size={14} />
                          {statusText}
                        </span>
                      </td>

                      {/* Expiration progress */}
                      <td style={{ padding: '16px', borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        {site.status !== 'error' && site.ssl_valid_to ? (
                          <div style={{ width: '100%' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.5)', marginBottom: '6px', fontWeight: '600' }}>
                              <span>{formatSimpleDate(site.ssl_valid_from)}</span>
                              <span>{formatSimpleDate(site.ssl_valid_to)}</span>
                            </div>
                            <div className="progress-container" style={{ height: '8px', backgroundColor: 'rgba(255, 255, 255, 0.05)', margin: 0 }}>
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

                      {/* Days Remaining */}
                      <td style={{ padding: '16px', borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        {site.status === 'error' ? (
                          <span style={{ color: 'var(--color-expired)', fontSize: '1rem', fontWeight: '700' }} title={site.last_error}>
                            {site.last_error?.slice(0, 25) || 'Connection Error'}...
                          </span>
                        ) : daysRemaining !== null ? (
                          <span 
                            style={{ 
                              fontWeight: '900', 
                              fontSize: '1.6rem', 
                              color: daysRemaining <= 0 ? 'var(--color-expired)' : daysRemaining <= site.warning_days ? 'var(--color-warning)' : 'var(--color-valid)',
                              textShadow: daysRemaining <= 0 ? '0 0 15px rgba(239, 68, 68, 0.7)' : 
                                          daysRemaining <= site.warning_days ? '0 0 15px rgba(245, 158, 11, 0.7)' : 'none'
                            }}
                          >
                            {Math.abs(daysRemaining)}{' '}
                            <span style={{ fontSize: '0.95rem', fontWeight: '700', color: 'rgba(255, 255, 255, 0.5)', textShadow: 'none' }}>
                              {daysRemaining < 0 ? t('db_days_expired') : t('db_days_left')}
                            </span>
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>—</span>
                        )}
                      </td>

                      {/* Issuer */}
                      <td style={{ padding: '16px', borderBottom: '1px solid rgba(255, 255, 255, 0.04)', fontSize: '1rem', color: 'rgba(255, 255, 255, 0.6)', fontWeight: '500' }}>
                        {site.ssl_issuer || '—'}
                      </td>

                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default TVDashboard;
