# 🛡️ Cert-Checker SSL Monitor

[![Stack](https://img.shields.io/badge/python-3.12-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/React-18-61DAFB.svg?style=for-the-badge&logo=react)](https://react.dev/)
[![Directory](https://img.shields.io/badge/Active%20Directory-LDAP-0078d4.svg?style=for-the-badge&logo=windows)](https://microsoft.com)
[![Docker](https://img.shields.io/badge/Docker-All--in--One-2496ED.svg?style=for-the-badge&logo=docker)](https://www.docker.com/)

Современная, быстрая и легковесная система мониторинга сроков действия SSL/TLS-сертификатов сетевой инфраструктуры. Поддерживает автоматический расчет дней до истечения, параллельные проверки (IPv4 / IPv6), интеграцию с корпоративным **Active Directory (LDAP)**, отправку умных алертов через Telegram/SMTP с защитой от спама и мониторинг через Zabbix LLD.

Вся система упакована в **единый компактный Docker-контейнер (All-in-One)** и оснащена гибкой системой тем (6 цветовых палитр + светлый/темный режимы в стиле Centralized Auth, Samba Web и OpenVPN Web).

<img width="1259" height="464" alt="image" src="https://github.com/user-attachments/assets/04cdab6c-dd0d-4266-9dc9-299cd2d52ac4" />

---

## ⚡ Основные возможности

* **All-in-One контейнеризация:** Единый контейнер запускает бэкенд FastAPI и нативно раздает собранный React SPA. Никаких лишних связок контейнеров или внешних Nginx.
* **Доменная авторизация Active Directory (LDAP):**
  * Вход по корпоративной почте (`user@domain.local`) или доменному логину (`DOMAIN\user` или `sAMAccountName`).
  * Фильтрация доступа по группе безопасности (`LDAP_REQUIRED_GROUP`) с поддержкой вложенных групп (`LDAP_MATCHING_RULE_IN_CHAIN` `1.2.840.113556.1.4.1941`).
  * Разграничение прав: администраторы (`LDAP_ADMIN_GROUP` или список `LDAP_ADMIN_USERS`) и наблюдатели (только чтение).
  * Резервный локальный вход (локальный `admin` доступен всегда, даже при недоступности контроллера домена).
* **Дизайн-система и 6 цветовых палитр (как в CA, Samba Web и OpenVPN Web):**
  * Переключение режима **Dark / Light**.
  * 6 профессиональных цветовых палитр с выпадающим меню предпросмотра:
    1. **Classic Zinc** (сдержанный графитовый);
    2. **Cyber Lime** (#0A0A0A + #B6FF00);
    3. **Electric Blue** (#101A46 + #245BFF);
    4. **Crimson Red** (#080808 + #C1121F);
    5. **Rust Orange** (#24150F + #D96B27);
    6. **Graphite Pink** (#292929 + #C88E9B).
* **Параллельная и надежная проверка:**
  * Поддержка **IPv4 и IPv6 (dual-stack)** без утечки сокетов.
  * Автоматическая нормализация входных данных хостов (очистка от `https://`, слэшей, пробелов, автоопределение портов).
  * Параллельная многопоточная проверка десятков сайтов за 1–2 секунды.
* **Режим ТВ / Монитора (`/tv`):** Полноэкранный информационный дашборд с часами для технических отделов и дежурных смен с неоновой подсветкой критических статусов.
* **Умные уведомления с дедупликацией:**
  * **Telegram:** отправка в чаты, группы, каналы и супергруппы с топиками (Thread ID).
  * **Email (SMTP):** поддержка STARTTLS и прямого SSL.
  * **Защита от флуда:** алерты отправляются только при смене уровня угрозы или по истечении кулдауна (раз в 3 дня), предотвращая спам каждые 12 часов.
* **Интеграция с Zabbix:** Автоматическое обнаружение (LLD `/api/v1/zabbix/discovery`) и отдача метрик в JSON (`/api/v1/zabbix/metrics`).

---

## 📂 Структура проекта

```text
/opt/cert-checker/
├── Dockerfile                        # Multi-stage сборка All-in-One (Node.js -> Python 3.12)
├── docker-compose.yml                # Файл быстрого развертывания единого контейнера
├── zabbix_template.yaml              # Шаблон Zabbix 6.x для импорта
├── zabbix_cert-checker_template.yaml # Шаблон Zabbix 7.x для импорта
├── .env.example                      # Пример конфигурации со всеми параметрами (вкл. AD/LDAP)
├── backend/                          # FastAPI бэкенд
│   ├── app/
│   │   ├── api/endpoints/            # Эндпоинты (auth, sites, users, zabbix)
│   │   ├── core/                     # Конфигурация, БД, безопасность
│   │   ├── models/                   # Модели SQLAlchemy
│   │   ├── schemas/                  # Pydantic схемы
│   │   └── services/                 # SSL-чекер, AD/LDAP авторизация, нотификатор
│   └── requirements.txt              # Зависимости Python
└── frontend/                         # React + Vite фронтенд
    ├── src/
    │   ├── components/               # Компоненты (PaletteDropdown и др.)
    │   ├── context/                  # AuthContext, ThemeContext, LanguageContext
    │   └── views/                    # Dashboard, AdminPanel, Login, TVDashboard
    └── package.json
```

---

## ⚙️ Конфигурация окружения (`.env`)

Все параметры настраиваются исключительно через файл `.env` (файл `docker-compose.yml` редактировать не требуется):

| Переменная | Описание | По умолчанию |
| :--- | :--- | :---: |
| **Сеть и Docker** | | |
| `BIND_HOST` | IP-адрес для привязки сервиса (`0.0.0.0` — все интерфейсы, `127.0.0.1` — локально) | `0.0.0.0` |
| `PORT` | Внешний веб-порт панели управления | `8080` |
| `DATA_PATH` | Каталог на хосте для постоянного хранения БД SQLite | `./data` |
| **Безопасность и БД** | | |
| `SECRET_KEY` | Секретный ключ подписи JWT токенов | *Замените в продакшне!* |
| `ZABBIX_TOKEN` | Токен авторизации для запросов Zabbix LLD | `zabbix_secret_token` |
| `DATABASE_URL` | URL подключения к БД (SQLite) | `sqlite:////data/cert_checker.db` |
| `FIRST_SUPERUSER_USERNAME` | Логин начального администратора | `admin` |
| `FIRST_SUPERUSER_PASSWORD` | Пароль начального администратора | `admin123` |
| **Active Directory / LDAP** | | |
| `LDAP_ENABLED` | Включить авторизацию через Active Directory (`true`/`false`) | `false` |
| `LDAP_SERVER` | Адрес контроллера домена (`ldap://10.11.4.254:389` или `ldaps://...`) | — |
| `LDAP_DOMAIN` | Домен AD (например, `corp.local`) | — |
| `LDAP_BASE_DN` | Базовый DN каталога (например, `DC=corp,DC=local`) | — |
| `LDAP_REQUIRED_GROUP` | Ограничение доступа по группе безопасности AD (опционально) | — |
| `LDAP_ADMIN_GROUP` | Группа безопасности AD для назначения роли администратора | — |
| `LDAP_ADMIN_USERS` | Список доменных логинов/почт администраторов через запятую | — |
| `LDAP_BIND_USER` | Сервисный аккаунт для поиска (`CN=svc,OU=...,DC=...`) | — |
| `LDAP_BIND_PASSWORD` | Пароль сервисного аккаунта | — |
| `LDAP_NESTED_GROUPS` | Рекурсивный поиск во вложенных группах AD | `true` |
| **Оповещения (SMTP)** | | |
| `SMTP_HOST` / `SMTP_PORT` | Хост и порт почтового сервера | — / `587` |
| `SMTP_USER` / `SMTP_PASSWORD` | Логин и пароль почтового ящика | — |
| `SMTP_TLS` | Использовать STARTTLS (`True` / `False`) | `True` |
| `EMAILS_FROM_EMAIL` | Адрес отправителя | `noreply@certchecker.local` |

---

## 🚀 Развертывание в Docker (All-in-One)

1. **Клонирование проекта:**
   ```bash
   git clone https://github.com/Ttolyanich/cert-checker.git /opt/cert-checker
   cd /opt/cert-checker
   ```

2. **Настройка окружения:**
   ```bash
   cp .env.example .env
   # Отредактируйте .env при необходимости
   nano .env
   ```

3. **Запуск единого контейнера:**
   ```bash
   docker compose up -d --build
   ```

Панель станет доступна по адресу `http://<IP_сервера>:8080`.
* По умолчанию создается локальный администратор: `admin` / `admin123`.
* Если включен LDAP, доступен бесшовный вход под доменными учетными записями AD.
