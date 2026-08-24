import logging
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def _send(to_email: str, subject: str, body: str) -> bool:
    settings = get_settings()

    # Gates on whether SMTP is actually configured, not on DEBUG -- the
    # old DEBUG-based bypass blocked real sending during normal local
    # testing, which also blocks Mailtrap Sandbox specifically (nothing
    # Sandbox receives ever reaches a real inbox, so that protection
    # wasn't buying any actual safety). Fill in SMTP_HOST/PORT/USERNAME/
    # PASSWORD and emails send for real, in DEBUG or not.
    smtp_configured = all(
        [settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]
    )

    if not smtp_configured:
        logger.info(f"[No SMTP configured -- logging instead] To: {to_email} | Subject: {subject}\n{body}")
        return True

    try:
        message = MIMEText(body, "plain")
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject

        # use_tls=False, start_tls=True is correct for Mailtrap's port
        # 2525 (STARTTLS, not implicit TLS).
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=False,
            start_tls=getattr(settings, "SMTP_STARTTLS", True),
            timeout=10,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email} via {settings.SMTP_HOST}:{settings.SMTP_PORT}: {e}")
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
