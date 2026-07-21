import logging
import smtplib
import ssl
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from typing import Optional

from .email_templates import EmailContent
from .smtp_config import SMTPConfig, get_smtp_config


logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when SMTP delivery fails after retry attempts."""


class EmailService:
    def __init__(self, config: Optional[SMTPConfig] = None):
        self.config = config or get_smtp_config()

    def build_message(self, to_email: str, content: EmailContent, unsubscribe_url: Optional[str] = None) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = self.config.sender
        msg["To"] = to_email
        msg["Subject"] = content.subject
        msg["Date"] = format_datetime(datetime.now(timezone.utc))
        msg["Message-ID"] = make_msgid(domain=self._message_domain())
        msg["Reply-To"] = self.config.reply_to
        msg["X-Mailer"] = "SocialHub FastAPI Mailer"
        msg["Auto-Submitted"] = "auto-generated"
        if unsubscribe_url:
            msg["List-Unsubscribe"] = f"<{unsubscribe_url}>, <mailto:{self.config.support_email}?subject=unsubscribe>"
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

        # Plain text first, then HTML alternative for deliverability.
        msg.set_content(content.text, subtype="plain", charset="utf-8")
        msg.add_alternative(content.html, subtype="html", charset="utf-8")
        return msg

    def send(self, to_email: str, content: EmailContent, *, raise_on_failure: bool = False, unsubscribe_url: Optional[str] = None) -> bool:
        if not self.config.enabled:
            logger.info("SMTP email skipped because EMAIL_HOST/EMAIL_USER/EMAIL_PASSWORD are not configured. to=%s subject=%s", to_email, content.subject)
            return False

        message = self.build_message(to_email, content, unsubscribe_url=unsubscribe_url)
        last_error: Optional[Exception] = None
        attempts = max(1, self.config.max_retries + 1)
        for attempt in range(1, attempts + 1):
            try:
                self._send_message(message)
                logger.info("SMTP email sent to=%s subject=%s message_id=%s", to_email, content.subject, message["Message-ID"])
                return True
            except Exception as exc:  # noqa: BLE001 - log and retry SMTP/network errors
                last_error = exc
                logger.warning("SMTP email attempt %s/%s failed to=%s subject=%s error=%s", attempt, attempts, to_email, content.subject, exc)
                if attempt < attempts:
                    time.sleep(min(2 ** (attempt - 1), 4))

        logger.error("SMTP email failed after retries to=%s subject=%s", to_email, content.subject, exc_info=last_error)
        if raise_on_failure:
            raise EmailDeliveryError("Email delivery failed") from last_error
        return False

    def _send_message(self, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        if self.config.use_ssl:
            with smtplib.SMTP_SSL(self.config.host, self.config.port, timeout=self.config.timeout_seconds, context=context) as server:
                server.login(self.config.username, self.config.password)
                server.send_message(message)
            return

        with smtplib.SMTP(self.config.host, self.config.port, timeout=self.config.timeout_seconds) as server:
            server.ehlo()
            if self.config.use_starttls:
                server.starttls(context=context)
                server.ehlo()
            server.login(self.config.username, self.config.password)
            server.send_message(message)

    def _message_domain(self) -> str:
        if "@" in self.config.sender_email:
            return self.config.sender_email.split("@", 1)[1]
        return "socialhub.local"


def get_email_service() -> EmailService:
    return EmailService()
