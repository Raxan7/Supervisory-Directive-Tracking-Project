import smtplib
from email.message import EmailMessage
from app.core.config import Settings


def send_email(settings: Settings, recipient: str, subject: str, body: str) -> bool:
    if not settings.smtp_enabled:
        return False
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
    return True

