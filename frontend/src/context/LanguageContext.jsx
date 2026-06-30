import React, { createContext, useContext, useState, useEffect } from 'react';

const LanguageContext = createContext();

const translations = {
  ru: {
    // Auth
    login_title: 'Вход в систему',
    login_subtitle: 'Панель администратора Cert-Checker',
    email_label: 'Имя пользователя',
    password_label: 'Пароль',
    btn_login: 'Войти',
    login_failed: 'Неверное имя пользователя или пароль',
    loading: 'Загрузка...',

    // Nav
    nav_dashboard: 'Главная',
    nav_admin: 'Панель управления',
    nav_tv: 'ТВ-Режим',
    nav_logout: 'Выйти',
    nav_login_btn: 'Войти в админку',

    // Dashboard Table
    db_title: 'Мониторинг SSL-сертификатов',
    db_no_sites: 'Список отслеживаемых сайтов пуст. Войдите в админку, чтобы добавить сайты.',
    db_checked_just_now: 'Только что',
    db_checked_ago: '{time} назад',
    db_status_valid: 'Действителен',
    db_status_warning: 'Истекает',
    db_status_expired: 'Истек',
    db_status_error: 'Ошибка',
    db_status_unchecked: 'Не проверен',
    db_days_left: 'дн. осталось',
    db_days_expired: 'дн. назад',
    db_btn_check: 'Проверить',
    db_btn_checking: 'Опрос...',
    
    tb_host: 'Доменное имя',
    tb_port: 'Порт',
    tb_status: 'Статус',
    tb_expiry: 'Срок действия',
    tb_days: 'Осталось дней',
    tb_issuer: 'Издатель',
    tb_checked: 'Проверен',
    tb_actions: 'Действия',
    
    // TV Mode
    tv_title: 'МОНИТОРИНГ SSL-СЕРТИФИКАТОВ',
    tv_active_alerts: 'Внимание',

    // Admin Panel
    admin_title: 'Управление мониторингом',
    tab_sites: 'Сайты',
    tab_notifications: 'Уведомления',
    tab_users: 'Администраторы',
    
    btn_add: 'Добавить сайт',
    btn_edit: 'Редактировать',
    btn_delete: 'Удалить',
    btn_save: 'Сохранить',
    btn_cancel: 'Отмена',
    
    confirm_delete: 'Вы уверены, что хотите удалить этот элемент?',
    
    // Admin - Sites
    site_host: 'Доменное имя (hostname)',
    site_port: 'Порт (по умолчанию 443)',
    site_warning: 'Предупреждать за (дней)',
    site_order: 'Порядок',
    
    // Admin - Users
    user_name: 'Имя',
    user_email: 'Логин',
    user_status: 'Статус',
    user_active: 'Активен',
    user_inactive: 'Заблокирован',
    user_password: 'Пароль (оставьте пустым для сохранения старого)',
    btn_add_user: 'Добавить админа',
    
    // Admin - Notifications
    notif_channel: 'Канал',
    notif_status: 'Состояние',
    notif_enabled: 'Включено',
    notif_disabled: 'Выключено',
    btn_add_notif: 'Добавить канал',
    notif_config: 'Параметры подключения (JSON)'
  },
  en: {
    // Auth
    login_title: 'Sign In',
    login_subtitle: 'Cert-Checker Administration',
    email_label: 'Username',
    password_label: 'Password',
    btn_login: 'Login',
    login_failed: 'Incorrect username or password',
    loading: 'Loading...',

    // Nav
    nav_dashboard: 'Home',
    nav_admin: 'Admin Panel',
    nav_tv: 'TV Mode',
    nav_logout: 'Logout',
    nav_login_btn: 'Admin Login',

    // Dashboard Table
    db_title: 'SSL Certificate Monitor',
    db_no_sites: 'No sites monitored yet. Log in to the Admin Panel to add sites.',
    db_checked_just_now: 'Just now',
    db_checked_ago: '{time} ago',
    db_status_valid: 'Valid',
    db_status_warning: 'Expiring',
    db_status_expired: 'Expired',
    db_status_error: 'Error',
    db_status_unchecked: 'Unchecked',
    db_days_left: 'days left',
    db_days_expired: 'days ago',
    db_btn_check: 'Verify',
    db_btn_checking: 'Checking...',
    
    tb_host: 'Domain Name',
    tb_port: 'Port',
    tb_status: 'Status',
    tb_expiry: 'Validity Period',
    tb_days: 'Days Remaining',
    tb_issuer: 'Issuer',
    tb_checked: 'Last Checked',
    tb_actions: 'Actions',
    
    // TV Mode
    tv_title: 'SSL CERTIFICATE MONITOR',
    tv_active_alerts: 'Warnings',

    // Admin Panel
    admin_title: 'Monitoring Settings',
    tab_sites: 'Sites',
    tab_notifications: 'Notifications',
    tab_users: 'Administrators',
    
    btn_add: 'Add Site',
    btn_edit: 'Edit',
    btn_delete: 'Delete',
    btn_save: 'Save Changes',
    btn_cancel: 'Cancel',
    
    confirm_delete: 'Are you sure you want to delete this item?',
    
    // Admin - Sites
    site_host: 'Domain Name (hostname)',
    site_port: 'Port (default 443)',
    site_warning: 'Warning Period (days)',
    site_order: 'Order',
    
    // Admin - Users
    user_name: 'Full Name',
    user_email: 'Username',
    user_status: 'Status',
    user_active: 'Active',
    user_inactive: 'Blocked',
    user_password: 'Password (leave blank to keep current)',
    btn_add_user: 'Add Admin',
    
    // Admin - Notifications
    notif_channel: 'Channel',
    notif_status: 'Status',
    notif_enabled: 'Enabled',
    notif_disabled: 'Disabled',
    btn_add_notif: 'Add Channel',
    notif_config: 'Connection Config (JSON)'
  }
};

export const LanguageProvider = ({ children }) => {
  const [lang, setLang] = useState(() => {
    const saved = localStorage.getItem('pref-lang');
    if (saved) return saved;
    
    const browserLang = navigator.language || navigator.userLanguage;
    return browserLang && browserLang.toLowerCase().startsWith('ru') ? 'ru' : 'en';
  });

  useEffect(() => {
    localStorage.setItem('pref-lang', lang);
  }, [lang]);

  const toggleLanguage = () => {
    setLang((prev) => (prev === 'ru' ? 'en' : 'ru'));
  };

  const t = (key, params = {}) => {
    let text = translations[lang][key] || translations['en'][key] || key;
    Object.keys(params).forEach((p) => {
      text = text.replace(`{${p}}`, params[p]);
    });
    return text;
  };

  return (
    <LanguageContext.Provider value={{ lang, toggleLanguage, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
