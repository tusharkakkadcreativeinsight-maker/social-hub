"""Backward-compatible email helpers built on the production SMTP service.

Sends ONLY one combined welcome + verification email during registration.
No duplicate emails are sent.
"""

from typing import Optional

from .email_service import get_email_service
from .email_templates import (
    EmailContent,
    create_account_email,
    forgot_password_otp,
    login_alert,
    password_reset_success,
    security_alert,
    verify_email_otp,
    welcome_email,
)
from .smtp_config import get_smtp_config


PUSH_NOTIFICATION_ENABLED: bool = False


def send_push_notification(device_token: str, title: str, body: str, data: Optional[dict] = None) -> bool:
    if not PUSH_NOTIFICATION_ENABLED:
        return False
    return False


def send_email(to_email: str, subject: str, html_content: str, from_email: Optional[str] = None, text_content: Optional[str] = None) -> bool:
    """Send a standards-compliant multipart email using the SMTP service."""
    content = EmailContent(subject=subject, html=html_content, text=text_content or subject)
    service = get_email_service()
    if from_email:
        service.config = service.config.__class__(**{**service.config.__dict__, "sender_email": from_email})
    return service.send(to_email, content)


def _urls(otp: str) -> tuple[str, str, str]:
    config = get_smtp_config()
    app_url = config.app_url
    return app_url, app_url, app_url


def send_create_account_email(to_email: str, username: str, otp: str) -> bool:
    """Send ONE combined welcome + verification OTP email (not multiple emails).

    This is the ONLY email sent during registration. It includes:
    - Welcome message
    - 6-digit verification OTP
    - Instructions to verify
    """
    config = get_smtp_config()
    app_url = config.app_url
    return get_email_service().send(
        to_email,
        create_account_email(username, otp, config.support_email, app_url)
    )


def send_verification_email(to_email: str, verification_token: str) -> bool:
    """Send email verification OTP/link. Name kept for existing imports."""
    config = get_smtp_config()
    app_url = config.app_url
    return get_email_service().send(
        to_email,
        verify_email_otp(verification_token, app_url, config.support_email)
    )


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send password reset OTP/link."""
    config = get_smtp_config()
    app_url = config.app_url
    return get_email_service().send(
        to_email,
        forgot_password_otp(reset_token, app_url, config.support_email)
    )


def send_password_reset_success_email(to_email: str) -> bool:
    config = get_smtp_config()
    return get_email_service().send(to_email, password_reset_success(config.support_email))


def send_welcome_email(to_email: str, username: str, otp: str = "") -> bool:
    """Send welcome email after successful registration.

    NOTE: This is now combined with verification email to avoid duplicates.
    Kept for backward compatibility but should NOT be called separately.
    """
    config = get_smtp_config()
    app_url = config.app_url
    return get_email_service().send(
        to_email,
        welcome_email(username, otp, app_url, config.support_email)
    )


def send_login_alert_email(to_email: str, time: str, device: str, browser: str, ip: Optional[str] = None, location: Optional[str] = None) -> bool:
    config = get_smtp_config()
    return get_email_service().send(to_email, login_alert(time, device, browser, ip, location, config.support_email))


def send_security_alert_email(to_email: str, title: str, message: str) -> bool:
    config = get_smtp_config()
    return get_email_service().send(to_email, security_alert(title, message, config.support_email))