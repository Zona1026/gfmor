from email.message import EmailMessage
import smtplib

from core.config import settings


def is_smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and (settings.SMTP_FROM or settings.SMTP_USERNAME))


def send_plain_email(to_email: str, subject: str, body: str) -> None:
    if not is_smtp_configured():
        raise RuntimeError("SMTP is not configured.")

    from_email = settings.SMTP_FROM or settings.SMTP_USERNAME
    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)
