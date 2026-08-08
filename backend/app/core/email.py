import logging
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def _send(to_email: str, subject: str, body: str) -> bool:
    settings = get_settings()

    if getattr(settings, "DEBUG", False):
        logger.info(f"[DEBUG email bypass] To: {to_email} | Subject: {subject}\n{body}")
        return True

    try:
        message = MIMEText(body, "plain")
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject

        # Port 465 is implicit TLS (SMTPS) -- connect already-encrypted, no
        # STARTTLS upgrade. Every other port (587, 2525/Mailtrap, 25) uses
        # STARTTLS, controlled by SMTP_STARTTLS. Hardcoding use_tls=False
        # here would break any host that actually needs port 465.
        implicit_tls = settings.SMTP_PORT == 465
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=implicit_tls,
            start_tls=False if implicit_tls else settings.SMTP_STARTTLS,
            timeout=10,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def send_verification_email(to_email: str, token: str) -> bool:
    settings = get_settings()
    url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    return await _send(
        to_email,
        f"Verify your email for {settings.APP_NAME}",
        f"Verify your email by visiting: {url}\n\nThis link expires in {settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS} hours.",
    )


async def send_password_reset_email(to_email: str, token: str) -> bool:
    settings = get_settings()
    url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    return await _send(
        to_email,
        f"Reset your password for {settings.APP_NAME}",
        f"Reset your password by visiting: {url}\n\nThis link expires in {settings.PASSWORD_RESET_TOKEN_TTL_MINUTES} minutes. If you didn't request this, ignore this email.",
    )


async def send_staff_invite_email(to_email: str, token: str) -> bool:
    settings = get_settings()
    url = f"{settings.FRONTEND_URL}/staff/accept-invite?token={token}"
    return await _send(
        to_email,
        f"You've been invited to {settings.APP_NAME}",
        f"You've been invited to join the team. Set your password here: {url}",
    )