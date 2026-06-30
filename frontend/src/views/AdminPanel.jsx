import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Shield, Sun, Moon, Globe, LogOut, Users, 
  Globe2, Bell, Plus, Edit2, Trash2, X, AlertCircle, ArrowUp, ArrowDown, RefreshCw, Send, Tv
} from 'lucide-react';

const AdminPanel = () => {
  const { user, token, logout } = useAuth();
  const { t, lang, toggleLanguage } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('sites'); // sites, notifications, users
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [checkingSiteId, setCheckingSiteId] = useState(null);
  const [testingNotifId, setTestingNotifId] = useState(null);
  
  // Data lists
  const [sites, setSites] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [usersList, setUsersList] = useState([]);

  // Modals state
  const [modalType, setModalType] = useState(null); // 'site', 'notification', 'user'
  const [modalMode, setModalMode] = useState('add'); // 'add', 'edit'
  const [selectedItem, setSelectedItem] = useState(null);

  // Form states
  const [siteForm, setSiteForm] = useState({ hostname: '', port: 443, warning_days: 14 });
  const [userForm, setUserForm] = useState({ username: '', full_name: '', password: '', is_active: true });
  const [notifForm, setNotifForm] = useState({
    channel_type: 'telegram',
    is_enabled: true,
    tg_bot_token: '',
    tg_chat_id: '',
    tg_thread_id: '',
    smtp_host: '',
    smtp_port: 587,
    smtp_user: '',
    smtp_password: '',
    smtp_use_tls: true,
    recipient_emails: ''
  });

  // --- API Fetching ---

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      
      // 1. Fetch Sites (ordered by order_index on backend)
      const sitesRes = await fetch('/api/v1/sites/', { headers });
      if (sitesRes.ok) {
        setSites(await sitesRes.json());
      }

      // 2. Fetch Notifications
      const notifRes = await fetch('/api/v1/sites/notifications/all', { headers });
      if (notifRes.ok) {
        setNotifications(await notifRes.json());
      }

      // 3. Fetch Users
      const usersRes = await fetch('/api/v1/users/', { headers });
      if (usersRes.ok) {
        setUsersList(await usersRes.json());
      }
    } catch (err) {
      setError('Failed to load data from server.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // --- Reordering Logic ---

  const handleMoveUp = async (siteId) => {
    try {
      const res = await fetch(`/api/v1/sites/${siteId}/move-up`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error('Error moving site up:', err);
    }
  };

  const handleMoveDown = async (siteId) => {
    try {
      const res = await fetch(`/api/v1/sites/${siteId}/move-down`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error('Error moving site down:', err);
    }
  };

  // --- Manual Verification Trigger ---

  const handleCheckSite = async (siteId) => {
    setCheckingSiteId(siteId);
    try {
      const res = await fetch(`/api/v1/sites/${siteId}/check`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error('Error checking site:', err);
    } finally {
      setCheckingSiteId(null);
    }
  };

  const handleTestNotification = async (configId) => {
    setTestingNotifId(configId);
    try {
      const res = await fetch(`/api/v1/sites/notifications/all/${configId}/test`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok) {
        alert(lang === 'ru' ? 'Тестовое оповещение успешно отправлено!' : 'Test notification sent successfully!');
      } else {
        alert(`${lang === 'ru' ? 'Ошибка отправки' : 'Failed to send'}: ${data.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error(err);
      alert('Network error trying to send test notification');
    } finally {
      setTestingNotifId(null);
    }
  };

  // --- CRUD Save Operations ---

  const handleSaveSite = async (e) => {
    e.preventDefault();
    const headers = { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
    try {
      let res;
      if (modalMode === 'add') {
        res = await fetch('/api/v1/sites/', {
          method: 'POST',
          headers,
          body: JSON.stringify(siteForm)
        });
      } else {
        res = await fetch(`/api/v1/sites/${selectedItem.id}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify({ 
            hostname: siteForm.hostname, 
            port: parseInt(siteForm.port), 
            warning_days: parseInt(siteForm.warning_days) 
          })
        });
      }
      
      if (res.ok) {
        setModalType(null);
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveNotification = async (e) => {
    e.preventDefault();
    const headers = { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
    
    // Construct config_json
    let configObj = {};
    if (notifForm.channel_type === 'telegram') {
      configObj = {
        bot_token: notifForm.tg_bot_token,
        chat_id: notifForm.tg_chat_id,
        thread_id: notifForm.tg_thread_id ? parseInt(notifForm.tg_thread_id) : null
      };
    } else if (notifForm.channel_type === 'email') {
      configObj = {
        smtp_host: notifForm.smtp_host,
        smtp_port: parseInt(notifForm.smtp_port),
        smtp_user: notifForm.smtp_user,
        smtp_password: notifForm.smtp_password,
        smtp_use_tls: notifForm.smtp_use_tls,
        recipient_emails: notifForm.recipient_emails
      };
    }

    const payload = {
      channel_type: notifForm.channel_type,
      is_enabled: notifForm.is_enabled,
      config_json: JSON.stringify(configObj)
    };

    try {
      let res;
      if (modalMode === 'add') {
        res = await fetch('/api/v1/sites/notifications/all', {
          method: 'POST',
          headers,
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch(`/api/v1/sites/notifications/all/${selectedItem.id}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify(payload)
        });
      }
      
      if (res.ok) {
        setModalType(null);
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveUser = async (e) => {
    e.preventDefault();
    const headers = { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
    try {
      let res;
      if (modalMode === 'add') {
        res = await fetch('/api/v1/users/', {
          method: 'POST',
          headers,
          body: JSON.stringify({ ...userForm, global_role: 'admin' })
        });
      } else {
        const updatePayload = { ...userForm };
        if (!updatePayload.password) delete updatePayload.password;
        
        res = await fetch(`/api/v1/users/${selectedItem.id}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify(updatePayload)
        });
      }
      
      if (res.ok) {
        setModalType(null);
        fetchData();
      } else {
        const data = await res.json();
        alert(`Error: ${data.detail || 'Failed to save user'}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteItem = async (type, id) => {
    if (!window.confirm(t('confirm_delete'))) return;
    
    const headers = { 'Authorization': `Bearer ${token}` };
    let url = '';
    
    if (type === 'site') url = `/api/v1/sites/${id}`;
    else if (type === 'notification') url = `/api/v1/sites/notifications/all/${id}`;
    else if (type === 'user') url = `/api/v1/users/${id}`;
    
    try {
      const res = await fetch(url, { method: 'DELETE', headers });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // --- Modal Helpers ---

  const openSiteModal = (mode, siteItem = null) => {
    setModalMode(mode);
    setSelectedItem(siteItem);
    if (mode === 'add') {
      setSiteForm({ hostname: '', port: 443, warning_days: 14 });
    } else {
      setSiteForm({ hostname: siteItem.hostname, port: siteItem.port, warning_days: siteItem.warning_days });
    }
    setModalType('site');
  };

  const openNotificationModal = (mode, notifItem = null) => {
    setModalMode(mode);
    setSelectedItem(notifItem);
    if (mode === 'add') {
      setNotifForm({
        channel_type: 'telegram',
        is_enabled: true,
        tg_bot_token: '',
        tg_chat_id: '',
        tg_thread_id: '',
        smtp_host: '',
        smtp_port: 587,
        smtp_user: '',
        smtp_password: '',
        smtp_use_tls: true,
        recipient_emails: ''
      });
    } else {
      const cfg = JSON.parse(notifItem.config_json);
      setNotifForm({
        channel_type: notifItem.channel_type,
        is_enabled: notifItem.is_enabled,
        tg_bot_token: notifItem.channel_type === 'telegram' ? cfg.bot_token : '',
        tg_chat_id: notifItem.channel_type === 'telegram' ? cfg.chat_id : '',
        tg_thread_id: (notifItem.channel_type === 'telegram' && cfg.thread_id) ? cfg.thread_id.toString() : '',
        smtp_host: notifItem.channel_type === 'email' ? cfg.smtp_host : '',
        smtp_port: notifItem.channel_type === 'email' ? cfg.smtp_port : 587,
        smtp_user: notifItem.channel_type === 'email' ? cfg.smtp_user : '',
        smtp_password: notifItem.channel_type === 'email' ? cfg.smtp_password : '',
        smtp_use_tls: notifItem.channel_type === 'email' ? cfg.smtp_use_tls : true,
        recipient_emails: notifItem.channel_type === 'email' ? cfg.recipient_emails : ''
      });
    }
    setModalType('notification');
  };

  const openUserModal = (mode, userItem = null) => {
    setModalMode(mode);
    setSelectedItem(userItem);
    if (mode === 'add') {
      setUserForm({ username: '', full_name: '', password: '', is_active: true });
    } else {
      setUserForm({ username: userItem.username, full_name: userItem.full_name || '', password: '', is_active: userItem.is_active });
    }
    setModalType('user');
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
            <Link to="/" className="nav-link">{t('nav_dashboard')}</Link>
            <Link to="/admin" className="nav-link active">{t('nav_admin')}</Link>
            <Link to="/tv" className="nav-link" target="_blank">
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Tv size={16} /> {t('nav_tv')}
              </span>
            </Link>
          </nav>

          <div className="header-controls">
            <span className="site-meta" style={{ marginRight: '8px' }}>{user?.username}</span>
            <button className="btn-icon" onClick={toggleLanguage} title="Switch Language">
              <Globe size={18} />
              <span style={{ fontSize: '0.75rem', fontWeight: 'bold', marginLeft: '4px' }}>
                {lang.toUpperCase()}
              </span>
            </button>
            <button className="btn-icon" onClick={toggleTheme} title="Toggle Theme">
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button className="btn-icon" onClick={logout} title={t('nav_logout')} style={{ color: 'var(--color-expired)' }}>
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container" style={{ flexGrow: 1, padding: '32px 24px' }}>
        <div style={{ display: 'flex', gap: '32px', alignItems: 'flex-start' }}>
          
          {/* Admin Sidebar */}
          <div className="card" style={{ width: '240px', padding: '12px', flexShrink: 0 }}>
            <button 
              className={`btn ${activeTab === 'sites' ? 'btn-primary' : 'btn-secondary'}`} 
              style={{ width: '100%', justifyContent: 'flex-start', marginBottom: '8px' }}
              onClick={() => setActiveTab('sites')}
            >
              <Globe2 size={16} />
              {t('tab_sites')}
            </button>

            <button 
              className={`btn ${activeTab === 'notifications' ? 'btn-primary' : 'btn-secondary'}`} 
              style={{ width: '100%', justifyContent: 'flex-start', marginBottom: '8px' }}
              onClick={() => setActiveTab('notifications')}
            >
              <Bell size={16} />
              {t('tab_notifications')}
            </button>

            <button 
              className={`btn ${activeTab === 'users' ? 'btn-primary' : 'btn-secondary'}`} 
              style={{ width: '100%', justifyContent: 'flex-start' }}
              onClick={() => setActiveTab('users')}
            >
              <Users size={16} />
              {t('tab_users')}
            </button>
          </div>

          {/* Tab Content */}
          <div style={{ flexGrow: 1 }}>
            
            {error && (
              <div className="badge error" style={{ padding: '12px 16px', borderRadius: 'var(--radius-sm)', width: '100%', marginBottom: '20px' }}>
                <AlertCircle size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
                {error}
              </div>
            )}

            {/* --- 1. SITES TAB --- */}
            {activeTab === 'sites' && (
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h3>{t('tab_sites')}</h3>
                  <button className="btn btn-primary" onClick={() => openSiteModal('add')}>
                    <Plus size={16} /> {t('btn_add')}
                  </button>
                </div>

                <div className="table-container">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>{t('site_host')}</th>
                        <th>{t('site_port')}</th>
                        <th>{t('site_warning')}</th>
                        <th style={{ width: '120px', textAlign: 'center' }}>{t('site_order')}</th>
                        <th style={{ width: '200px', textAlign: 'right' }}>{t('tb_actions')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sites.map((s, index) => {
                        const isChecking = checkingSiteId === s.id;
                        return (
                          <tr key={s.id}>
                            <td><b>{s.hostname}</b></td>
                            <td><code>{s.port}</code></td>
                            <td>{s.warning_days} {lang === 'ru' ? 'дн.' : 'days'}</td>
                            <td style={{ textAlign: 'center' }}>
                              <div style={{ display: 'inline-flex', gap: '4px' }}>
                                <button 
                                  className="btn-icon" 
                                  onClick={() => handleMoveUp(s.id)} 
                                  disabled={index === 0}
                                  style={{ width: '28px', height: '28px', opacity: index === 0 ? 0.3 : 1 }}
                                >
                                  <ArrowUp size={12} />
                                </button>
                                <button 
                                  className="btn-icon" 
                                  onClick={() => handleMoveDown(s.id)} 
                                  disabled={index === sites.length - 1}
                                  style={{ width: '28px', height: '28px', opacity: index === sites.length - 1 ? 0.3 : 1 }}
                                >
                                  <ArrowDown size={12} />
                                </button>
                              </div>
                            </td>
                            <td>
                              <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                                <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '0.8rem' }} onClick={() => handleCheckSite(s.id)} disabled={isChecking}>
                                  <RefreshCw size={12} className={isChecking ? 'spin' : ''} style={{ marginRight: '4px' }} />
                                  {isChecking ? t('db_btn_checking') : t('db_btn_check')}
                                </button>
                                <button className="btn-icon" onClick={() => openSiteModal('edit', s)} title={t('btn_edit')} style={{ width: '32px', height: '32px' }}>
                                  <Edit2 size={14} />
                                </button>
                                <button className="btn-icon" onClick={() => handleDeleteItem('site', s.id)} title={t('btn_delete')} style={{ width: '32px', height: '32px', color: 'var(--color-expired)' }}>
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* --- 2. NOTIFICATIONS TAB --- */}
            {activeTab === 'notifications' && (
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h3>{t('tab_notifications')}</h3>
                  <button className="btn btn-primary" onClick={() => openNotificationModal('add')}>
                    <Plus size={16} /> {t('btn_add_notif')}
                  </button>
                </div>

                <div className="table-container">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>{t('notif_channel')}</th>
                        <th>{t('notif_status')}</th>
                        <th style={{ width: '200px', textAlign: 'right' }}>{t('tb_actions')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {notifications.map(n => (
                        <tr key={n.id}>
                          <td>
                            <span className="badge error" style={{ textTransform: 'uppercase', background: 'var(--accent-glow)', color: 'var(--accent-color)' }}>
                              {n.channel_type}
                            </span>
                          </td>
                          <td>
                            <span className={`badge ${n.is_enabled ? 'valid' : 'unchecked'}`}>
                              {n.is_enabled ? t('notif_enabled') : t('notif_disabled')}
                            </span>
                          </td>
                          <td>
                            <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                              <button 
                                className="btn btn-secondary" 
                                style={{ padding: '4px 10px', fontSize: '0.8rem' }} 
                                onClick={() => handleTestNotification(n.id)} 
                                disabled={testingNotifId === n.id}
                              >
                                <Send size={12} className={testingNotifId === n.id ? 'spin' : ''} style={{ marginRight: '4px' }} />
                                {testingNotifId === n.id ? t('loading') : (lang === 'ru' ? 'Тест' : 'Test')}
                              </button>
                              <button className="btn-icon" onClick={() => openNotificationModal('edit', n)} title={t('btn_edit')} style={{ width: '32px', height: '32px' }}>
                                <Edit2 size={14} />
                              </button>
                              <button className="btn-icon" onClick={() => handleDeleteItem('notification', n.id)} title={t('btn_delete')} style={{ width: '32px', height: '32px', color: 'var(--color-expired)' }}>
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* --- 3. ADMINISTRATORS TAB --- */}
            {activeTab === 'users' && (
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h3>{t('tab_users')}</h3>
                  <button className="btn btn-primary" onClick={() => openUserModal('add')}>
                    <Plus size={16} /> {t('btn_add_user')}
                  </button>
                </div>

                <div className="table-container">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>{t('user_name')}</th>
                        <th>{t('user_email')}</th>
                        <th>{t('user_status')}</th>
                        <th style={{ width: '120px', textAlign: 'right' }}>{t('tb_actions')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {usersList.map(u => (
                        <tr key={u.id}>
                          <td><b>{u.full_name || '—'}</b></td>
                          <td>{u.username}</td>
                          <td>
                            <span className={`badge ${u.is_active ? 'valid' : 'expired'}`}>
                              {u.is_active ? t('user_active') : t('user_inactive')}
                            </span>
                          </td>
                          <td>
                            <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                              <button className="btn-icon" onClick={() => openUserModal('edit', u)} title={t('btn_edit')} style={{ width: '32px', height: '32px' }}>
                                <Edit2 size={14} />
                              </button>
                              {usersList.length > 1 && u.id !== user.id && (
                                <button className="btn-icon" onClick={() => handleDeleteItem('user', u.id)} title={t('btn_delete')} style={{ width: '32px', height: '32px', color: 'var(--color-expired)' }}>
                                  <Trash2 size={14} />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

          </div>
        </div>
      </main>

      {/* --- MODALS --- */}
      {modalType && (
        <div className="modal-overlay">
          <div className="modal-content">
            
            <div className="modal-header">
              <h4>
                {modalType === 'site' ? `${modalMode === 'add' ? t('btn_add') : t('btn_edit')}` : ''}
                {modalType === 'notification' ? `${modalMode === 'add' ? t('btn_add_notif') : t('btn_edit')}` : ''}
                {modalType === 'user' ? `${modalMode === 'add' ? t('btn_add_user') : t('btn_edit')}` : ''}
              </h4>
              <button className="btn-icon" onClick={() => setModalType(null)} style={{ border: 'none' }}>
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            
            {/* 1. SITE MODAL */}
            {modalType === 'site' && (
              <form onSubmit={handleSaveSite}>
                <div className="modal-body">
                  <div className="form-group">
                    <label className="form-label">{t('site_host')}</label>
                    <input type="text" className="form-control" required placeholder="example.com" value={siteForm.hostname} onChange={e => setSiteForm({...siteForm, hostname: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('site_port')}</label>
                    <input type="number" className="form-control" required value={siteForm.port} onChange={e => setSiteForm({...siteForm, port: parseInt(e.target.value) || 443})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('site_warning')}</label>
                    <input type="number" className="form-control" required value={siteForm.warning_days} onChange={e => setSiteForm({...siteForm, warning_days: parseInt(e.target.value) || 14})} />
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setModalType(null)}>{t('btn_cancel')}</button>
                  <button type="submit" className="btn btn-primary">{t('btn_save')}</button>
                </div>
              </form>
            )}

            {/* 2. NOTIFICATION MODAL */}
            {modalType === 'notification' && (
              <form onSubmit={handleSaveNotification}>
                <div className="modal-body" style={{ maxHeight: '420px', overflowY: 'auto' }}>
                  <div className="form-group">
                    <label className="form-label">{t('notif_channel')}</label>
                    <select className="form-control" value={notifForm.channel_type} onChange={e => setNotifForm({...notifForm, channel_type: e.target.value})}>
                      <option value="telegram">Telegram</option>
                      <option value="email">Email (SMTP)</option>
                    </select>
                  </div>

                  {notifForm.channel_type === 'telegram' && (
                    <>
                      <div className="form-group">
                        <label className="form-label">Telegram Bot Token</label>
                        <input type="text" className="form-control" required placeholder="123456789:ABCDefGh..." value={notifForm.tg_bot_token} onChange={e => setNotifForm({...notifForm, tg_bot_token: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Telegram Chat ID</label>
                        <input type="text" className="form-control" required placeholder="-100123456789 or 98765432" value={notifForm.tg_chat_id} onChange={e => setNotifForm({...notifForm, tg_chat_id: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Topic ID (Message Thread ID) - Optional</label>
                        <input type="number" className="form-control" placeholder="123" value={notifForm.tg_thread_id} onChange={e => setNotifForm({...notifForm, tg_thread_id: e.target.value})} />
                      </div>
                    </>
                  )}

                  {notifForm.channel_type === 'email' && (
                    <>
                      <div className="form-group">
                        <label className="form-label">SMTP Host</label>
                        <input type="text" className="form-control" required placeholder="smtp.mail.ru" value={notifForm.smtp_host} onChange={e => setNotifForm({...notifForm, smtp_host: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">SMTP Port</label>
                        <input type="number" className="form-control" required placeholder="587" value={notifForm.smtp_port} onChange={e => setNotifForm({...notifForm, smtp_port: parseInt(e.target.value) || 587})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">SMTP User</label>
                        <input type="text" className="form-control" required placeholder="alert@yourcompany.ru" value={notifForm.smtp_user} onChange={e => setNotifForm({...notifForm, smtp_user: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">SMTP Password</label>
                        <input type="password" className="form-control" placeholder="SMTP Password" value={notifForm.smtp_password} onChange={e => setNotifForm({...notifForm, smtp_password: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Recipient Emails (comma-separated)</label>
                        <input type="text" className="form-control" required placeholder="admin@yourcompany.ru, manager@yourcompany.ru" value={notifForm.recipient_emails} onChange={e => setNotifForm({...notifForm, recipient_emails: e.target.value})} />
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px' }}>
                        <input type="checkbox" id="smtpTls" checked={notifForm.smtp_use_tls} onChange={e => setNotifForm({...notifForm, smtp_use_tls: e.target.checked})} />
                        <label htmlFor="smtpTls" className="form-label" style={{ margin: 0 }}>Use TLS</label>
                      </div>
                    </>
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '16px' }}>
                    <input type="checkbox" id="notifEnabled" checked={notifForm.is_enabled} onChange={e => setNotifForm({...notifForm, is_enabled: e.target.checked})} />
                    <label htmlFor="notifEnabled" className="form-label" style={{ margin: 0 }}>{t('notif_enabled')}</label>
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setModalType(null)}>{t('btn_cancel')}</button>
                  <button type="submit" className="btn btn-primary">{t('btn_save')}</button>
                </div>
              </form>
            )}

            {/* 3. USER MODAL */}
            {modalType === 'user' && (
              <form onSubmit={handleSaveUser}>
                <div className="modal-body">
                  <div className="form-group">
                    <label className="form-label">{t('user_email')}</label>
                    <input type="text" className="form-control" required value={userForm.username} onChange={e => setUserForm({...userForm, username: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('user_name')}</label>
                    <input type="text" className="form-control" value={userForm.full_name} onChange={e => setUserForm({...userForm, full_name: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{t('user_password')}</label>
                    <input type="password" className="form-control" required={modalMode === 'add'} value={userForm.password} onChange={e => setUserForm({...userForm, password: e.target.value})} />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '16px' }}>
                    <input type="checkbox" id="isActive" checked={userForm.is_active} onChange={e => setUserForm({...userForm, is_active: e.target.checked})} />
                    <label htmlFor="isActive" className="form-label" style={{ margin: 0 }}>{t('user_active')}</label>
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setModalType(null)}>{t('btn_cancel')}</button>
                  <button type="submit" className="btn btn-primary">{t('btn_save')}</button>
                </div>
              </form>
            )}

          </div>
        </div>
      )}
      
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

export default AdminPanel;
