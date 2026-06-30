import json
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings

def send_telegram_message(
    bot_token: str,
    chat_id: str,
    message: str,
    thread_id: Optional[int] = None
) -> bool:
    """
    Sends a message via Telegram Bot API.
    Supports chat_id (PM, group, channel) and message_thread_id (for group topics).
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if thread_id:
        payload["message_thread_id"] = thread_id
        
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")
        return False


def send_email(
    subject: str,
    body: str,
    recipients: list[str],
    smtp_config: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Sends an email notification via SMTP.
    If smtp_config is not provided, uses global system settings.
    """
    # Fallback to global settings
    host = smtp_config.get("smtp_host") if smtp_config else settings.SMTP_HOST
    port = smtp_config.get("smtp_port") if smtp_config else settings.SMTP_PORT
    user = smtp_config.get("smtp_user") if smtp_config else settings.SMTP_USER
    password = smtp_config.get("smtp_password") if smtp_config else settings.SMTP_PASSWORD
    use_tls = smtp_config.get("smtp_use_tls", True) if smtp_config else settings.SMTP_TLS
    
    # If custom SMTP config is used, default the sender email to the SMTP username
    from_email = None
    if smtp_config:
        from_email = smtp_config.get("from_email") or smtp_config.get("smtp_user")
    
    if not from_email:
        from_email = settings.EMAILS_FROM_EMAIL
        
    if not from_email:
        from_email = user or "noreply@certchecker.local"
        
    from_name = smtp_config.get("from_name") if smtp_config else None
    if not from_name:
        from_name = settings.EMAILS_FROM_NAME
    if not from_name:
        from_name = "Cert-Checker"

    if not host or not port or not user or not password or not from_email:
        print("SMTP settings are incomplete. Skipping email notification.")
        return False

    msg = MIMEText(body, "html", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = f'"{from_name}" <{from_email}>'
    msg["To"] = ", ".join(recipients)

    try:
        # Connect to SMTP server
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
            
        server.login(user, password)
        server.sendmail(from_email, recipients, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending Email notification: {e}")
        return False


def dispatch_alert(
    hostname: str,
    days_remaining: int,
    status: str,
    warning_days: int,
    config: Dict[str, Any]
) -> bool:
    """
    Dispatches alert depending on the configuration channel.
    """
    channel_type = config.get("channel_type")
    is_enabled = config.get("is_enabled", True)
    
    if not is_enabled:
        return False
        
    try:
        cfg = json.loads(config.get("config_json", "{}"))
    except Exception:
        print("Failed to parse notification config_json.")
        return False

    # Generate message content
    if status == "expired":
        subject_ru = f"❌ СРОЧНО: Истек SSL-сертификат {hostname}"
        subject_en = f"❌ URGENT: SSL Certificate Expired for {hostname}"
        
        body_ru = (
            f"<b>Критическое оповещение!</b><br>"
            f"Срок действия SSL-сертификата для сайта <b>{hostname}</b> ИСТЕК!<br>"
            f"Сайт сейчас может отображаться как небезопасный для пользователей.<br>"
            f"Пожалуйста, обновите сертификат как можно быстрее."
        )
        body_en = (
            f"<b>Critical Alert!</b><br>"
            f"SSL Certificate for <b>{hostname}</b> has EXPIRED!<br>"
            f"The site may now be displayed as insecure to users.<br>"
            f"Please renew the certificate as soon as possible."
        )
    elif status == "error":
        subject_ru = f"⚠️ Ошибка проверки SSL-сертификата: {hostname}"
        subject_en = f"⚠️ SSL Verification Error: {hostname}"
        
        err_msg = config.get("last_error", "Unknown connection error")
        body_ru = (
            f"<b>Внимание!</b><br>"
            f"Не удалось проверить SSL-сертификат для сайта <b>{hostname}</b>.<br>"
            f"Детали ошибки: <code>{err_msg}</code><br>"
            f"Пожалуйста, проверьте доступность сайта."
        )
        body_en = (
            f"<b>Warning!</b><br>"
            f"Failed to verify SSL certificate for <b>{hostname}</b>.<br>"
            f"Error details: <code>{err_msg}</code><br>"
            f"Please check the site availability."
        )
    else:
        subject_ru = f"⏰ Предупреждение: Сертификат {hostname} истекает через {days_remaining} дн."
        subject_en = f"⏰ Warning: Certificate for {hostname} expires in {days_remaining} days"
        
        body_ru = (
            f"<b>Оповещение об истечении сертификата</b><br>"
            f"SSL-сертификат для сайта <b>{hostname}</b> истекает менее чем через {warning_days} дней.<br>"
            f"Осталось дней: <b>{days_remaining}</b>.<br>"
            f"Пожалуйста, запланируйте обновление сертификата."
        )
        body_en = (
            f"<b>Certificate Expiration Warning</b><br>"
            f"SSL certificate for <b>{hostname}</b> will expire in less than {warning_days} days.<br>"
            f"Days remaining: <b>{days_remaining}</b>.<br>"
            f"Please plan to renew the certificate."
        )

    # Dispatch
    if channel_type == "telegram":
        bot_token = cfg.get("bot_token")
        chat_id = cfg.get("chat_id")
        thread_id = cfg.get("thread_id")
        
        if not bot_token or not chat_id:
            return False
            
        # Compile plain text version of body for Telegram (since it supports HTML)
        # Combine RU and EN for universal notifications
        tg_message = f"{subject_ru}\n\n{body_ru.replace('<br>', '\n')}\n\n---\n\n{subject_en}\n\n{body_en.replace('<br>', '\n')}"
        return send_telegram_message(bot_token, chat_id, tg_message, thread_id)
        
    elif channel_type == "email":
        recipients_str = cfg.get("recipient_emails", "")
        recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
        
        if not recipients:
            return False
            
        # Construct HTML email body
        email_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="margin-top: 0;">{subject_ru}</h2>
                <p>{body_ru}</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <h2>{subject_en}</h2>
                <p>{body_en}</p>
            </div>
        </body>
        </html>
        """
        # Combine subjects
        combined_subject = f"{subject_ru} / {subject_en}"
        return send_email(combined_subject, email_html, recipients, cfg)
        
    return False
