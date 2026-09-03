import smtplib
from email.mime.text import MIMEText
from typing import Literal

from app.core.config import settings


def send_email(to: str, subject: str, body: str) -> None:
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.smtp_from_address]):
        raise RuntimeError("SMTP is not configured")
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_address}>"
    msg["To"] = to
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def send_otp_email(to: str, otp: str) -> None:
    send_email(
        to=to,
        subject="Your Aarogya verification code",
        body=f"Your verification code is {otp}. It expires in 10 minutes.",
    )
