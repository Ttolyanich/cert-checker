# 🛡️ Cert-Checker SSL Monitor

[![Stack](https://img.shields.io/badge/python-3.12-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/FastAPI-0.109%2B-009688.svg?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/React-18-61DAFB.svg?style=for-the-badge&logo=react)](https://react.dev/)
[![Database](https://img.shields.io/badge/SQLite-3-blue.svg?style=for-the-badge&logo=sqlite)](https://www.sqlite.org/)

Современная, быстрая и легкая система мониторинга сроков действия SSL/TLS-сертификатов. Предназначена для контроля сетевой инфраструктуры с автоматическим расчетом дней до истечения, интеграцией с Zabbix и оповещениями через Telegram/SMTP. Интерфейс выполнен в премиальном стиле Vercel/Linear (строгая темная/светлая тема).

---

## ⚡ Основные возможности

* **Мгновенная проверка:** SSL-сертификат опрашивается и рассчитывается сразу при добавлении домена.
* **Функциональный дашборд:** Интерактивная таблица с прогресс-баром, статусом (валиден/истекает/просрочен/ошибка), CA издателем и датами действия.
* **Режим ТВ / Монитора (`/tv`):** Полноэкранный темный интерфейс для технических отделов с крупными шрифтами и пульсирующей неоновой подсветкой доменов с ошибками.
* **Умные уведомления:**
  * **Telegram:** Отправка алертов в группы, каналы и конкретные топики (Thread ID).
  * **Email (SMTP):** Поддержка STARTTLS и SSL, обход спам-фильтров через подстановку авторизованного отправителя.
* **Интеграция с Zabbix:** Автоматическое обнаружение сайтов (LLD) и передача метрик в JSON с нулевой нагрузкой.

---

## 📂 Структура проекта

```text
/opt/cert-checker/
├── docker-compose.yml              # Файл Docker Compose для запуска бэкенда и фронтенда
├── zabbix_template.yaml            # Шаблон Zabbix 6.x для импорта
├── zabbix_cert-checker_template.yaml # Шаблон Zabbix 7.x для импорта
├── .env.example                    # Пример файла конфигурации бэкенда
├── backend/                        # Бэкенд на Python (FastAPI + SQLAlchemy)
│   ├── app/                        # Модули приложения
│   └── Dockerfile                  # Инструкция сборки бэкенда
└── frontend/                       # Фронтенд на React + Vite
    ├── src/                        # Исходный код интерфейса
    └── Dockerfile                  # Инструкция сборки фронтенда (Nginx)
```

---

## ⚙️ Конфигурация окружения (`.env`)

Создайте файл `.env` в папке бэкенда на основе шаблона `.env.example`:

| Переменная | Описание | Значение по умолчанию |
| :--- | :--- | :---: |
| `SECRET_KEY` | Секретный ключ подписи токенов бэкенда | `prod_super_secret_key...` |
| `ZABBIX_TOKEN` | Секретный токен для авторизации запросов Zabbix LLD | `zabbix_secret_token` |
| `DATABASE_URL` | URL подключения к БД (SQLite) | `sqlite:////data/cert_checker.db` |
| `FIRST_SUPERUSER_USERNAME` | Логин администратора по умолчанию | `admin` |
| `FIRST_SUPERUSER_PASSWORD` | Стартовый пароль администратора | `admin123` |
| `SMTP_HOST` / `SMTP_PORT` | Хост и порт для отправки Email-уведомлений | - / `587` |
| `SMTP_USER` / `SMTP_PASSWORD` | Учетные данные почтового ящика (SMTP) | - |
| `SMTP_TLS` | Использовать шифрование TLS (`True` / `False`) | `True` |

---

## 🚀 Варианты развертывания

### Вариант 1. Быстрый старт через Docker (Рекомендуемый)

1. **Клонирование проекта:**
   ```bash
   git clone https://github.com/Ttolyanich/cert-checker.git /opt/cert-checker
   cd /opt/cert-checker
   ```
2. **Запуск:**
   ```bash
   docker compose up -d
   ```
   Панель станет доступна по адресу `http://<IP_сервера>:8080` (логин `admin` / пароль `admin123`).

### Вариант 2. Запуск напрямую на хосте

#### Бэкенд:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

#### Фронтенд:
```bash
cd frontend
npm install
npm run build
# Настройте Nginx для раздачи папки /dist и проксирования запросов /api на порт 8000
```
