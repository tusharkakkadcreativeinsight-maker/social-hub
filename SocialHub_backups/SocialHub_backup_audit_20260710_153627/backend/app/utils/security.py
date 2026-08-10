import bcrypt
import secrets
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from ..config import settings


def _fernet_key() -> bytes:
    """Derive a stable Fernet key from APP_SECRET_KEY for local token encryption."""
    digest = hashlib.sha256(settings.APP_SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(value: str) -> str:
    """Encrypt sensitive provider tokens before storing them in the database."""
    if not value:
        return ""
    from cryptography.fernet import Fernet
    return Fernet(_fernet_key()).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    """Decrypt sensitive provider tokens for authorized server-side API calls."""
    if not value:
        return ""
    from cryptography.fernet import Fernet, InvalidToken
    try:
        return Fernet(_fernet_key()).decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access", "jti": secrets.token_hex(16)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": secrets.token_hex(16)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None


def create_verification_token(email: str) -> str:
    return create_access_token(
        {"sub": email, "purpose": "email_verification"},
        timedelta(hours=24)
    )


def create_password_reset_token(email: str) -> str:
    return create_access_token(
        {"sub": email, "purpose": "password_reset"},
        timedelta(hours=1)
    )


def generate_2fa_secret() -> str:
    """Generate an RFC 3548 base32 TOTP secret."""
    import pyotp
    return pyotp.random_base32()


def generate_2fa_qr_url(username: str, secret: str) -> str:
    """Generate a TOTP URL for QR code generation."""
    import pyotp
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=settings.APP_NAME)


def verify_2fa_code(secret: str, code: str) -> bool:
    """Verify a TOTP code using pyotp."""
    try:
        import pyotp
        return pyotp.TOTP(secret).verify(str(code).strip(), valid_window=1)
    except Exception:
        return False


def generate_device_info(user_agent: str) -> str:
    """Parse user agent to get basic device info."""
    ua = user_agent.lower()
    if "mobile" in ua or "android" in ua:
        device = "Mobile"
    elif "windows" in ua:
        device = "Windows"
    elif "mac" in ua:
        device = "Mac"
    elif "linux" in ua:
        device = "Linux"
    else:
        device = "Unknown"

    if "chrome" in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua:
        browser = "Safari"
    elif "edge" in ua:
        browser = "Edge"
    else:
        browser = "Unknown"

    return f"{device} - {browser}"