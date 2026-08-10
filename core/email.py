from email.message import EmailMessage
from email.utils import formataddr, parseaddr
import smtplib

from core.config import settings


def _sender_address() -> str:
    raw_sender = settings.SMTP_FROM or settings.SMTP_USERNAME
    if not raw_sender:
        raise RuntimeError("SMTP sender is not configured.")

    parsed_name, parsed_email = parseaddr(raw_sender)
    if not parsed_email or "@" not in parsed_email:
        raise RuntimeError("SMTP_FROM must be an email address, for example no-reply@example.com.")

    display_name = settings.SMTP_FROM_NAME or parsed_name
    if display_name:
        return formataddr((display_name, parsed_email))
    return parsed_email


def is_smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and (settings.SMTP_FROM or settings.SMTP_USERNAME))


def send_plain_email(to_email: str, subject: str, body: str) -> None:
    if not is_smtp_configured():
        raise RuntimeError("SMTP is not configured.")

    from_email = _sender_address()
    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        server.ehlo()
        if settings.SMTP_USE_TLS:
            server.starttls()
            server.ehlo()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)
