import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from .security import hash_password, verify_password


OTP_EXPIRY_MINUTES = 10


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    return hash_password(str(otp).strip())


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    if not plain_otp or not hashed_otp:
        return False
    return verify_password(str(plain_otp).strip(), hashed_otp)


def create_otp_expiry(minutes: int = OTP_EXPIRY_MINUTES) -> datetime:
    return utcnow_naive() + timedelta(minutes=minutes)


def is_otp_expired(expires_at: Optional[datetime]) -> bool:
    return not expires_at or expires_at < utcnow_naive()


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(str(left or ""), str(right or ""))
