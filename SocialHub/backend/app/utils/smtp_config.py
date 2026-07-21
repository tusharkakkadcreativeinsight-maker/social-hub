import os
import logging
from dataclasses import dataclass, replace
from email.utils import formataddr
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SMTPConfig:
    """SMTP settings loaded exclusively from environment variables.

    No credentials are ever hardcoded. EMAIL_FROM and EMAIL_USER must
    match for Gmail. The password is never printed in logs.
    """

    host: str
    port: int
    username: str
    password: str
    sender_email: str
    sender_name: str
    reply_to: str
    support_email: str
    app_url: str
    use_ssl: bool = False
    use_starttls: bool = True
    timeout_seconds: int = 20
    max_retries: int = 2

    @property
    def enabled(self) -> bool:
        return bool(self.host and self.port and self.username and self.password and self.sender_email)

    @property
    def sender(self) -> str:
        return formataddr((self.sender_name, self.sender_email))


def get_smtp_config() -> SMTPConfig:
    """Build SMTPConfig from environment variables only.

    For Gmail:
      EMAIL_HOST=smtp.gmail.com
      EMAIL_PORT=587
      EMAIL_USER= tusharkakkad.creativeinsight@gmail.com
      EMAIL_PASSWORD=ntqqjnrfncnlfatb
      EMAIL_FROM= tusharkakkad.creativeinsight@gmail.com
      EMAIL_FROM_NAME=SocialHub Security
      EMAIL_USE_STARTTLS=true
      EMAIL_USE_SSL=false
      APP_URL=http://localhost:8000

    EMAIL_FROM falls back to EMAIL_USER if not set (required for Gmail).
    """
    host = os.getenv("EMAIL_HOST", "")
    port_str = os.getenv("EMAIL_PORT", "587")
    username = os.getenv("EMAIL_USER", "tusharkakkad.creativeinsight@gmail.com")
    password = os.getenv("EMAIL_PASSWORD", "ntqqjnrfncnlfatb")
    sender_email = os.getenv("EMAIL_FROM", "") or username
    sender_name = os.getenv("EMAIL_FROM_NAME", "SocialHub Security")
    reply_to = os.getenv("EMAIL_REPLY_TO", "") or sender_email
    support_email = os.getenv("SUPPORT_EMAIL", "") or sender_email
    app_url = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")
    use_starttls_str = os.getenv("EMAIL_USE_STARTTLS", "true")
    use_ssl_str = os.getenv("EMAIL_USE_SSL", "false")

    try:
        port = int(port_str)
    except (ValueError, TypeError):
        port = 587

    use_starttls = use_starttls_str.strip().lower() in {"1", "true", "yes", "on"}
    use_ssl = use_ssl_str.strip().lower() in {"1", "true", "yes", "on"}

    timeout_str = os.getenv("EMAIL_TIMEOUT_SECONDS", "20")
    try:
        timeout_seconds = int(timeout_str)
    except (ValueError, TypeError):
        timeout_seconds = 20

    retries_str = os.getenv("EMAIL_MAX_RETRIES", "2")
    try:
        max_retries = int(retries_str)
    except (ValueError, TypeError):
        max_retries = 2

    if not host or not username or not password:
        logger.info(
            "SMTP email disabled: EMAIL_HOST, EMAIL_USER, and EMAIL_PASSWORD "
            "must be set in environment. to send real emails, configure these "
            "in your .env file."
        )

    return SMTPConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        sender_email=sender_email,
        sender_name=sender_name,
        reply_to=reply_to,
        support_email=support_email,
        app_url=app_url,
        use_ssl=use_ssl,
        use_starttls=use_starttls,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )