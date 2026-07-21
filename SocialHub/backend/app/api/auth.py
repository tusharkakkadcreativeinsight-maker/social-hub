from fastapi import APIRouter, Depends, HTTPException, status, Request as FastAPIRequest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
import secrets
import logging

from ..database import get_db
from ..models.models import User, Profile, LoginHistory, ActiveSession, NotificationSetting
from ..schemas.schemas import (
    RegisterRequest, LoginRequest, Token, VerifyEmailRequest,
    ForgotPasswordRequest, ResetPasswordRequest, RefreshTokenRequest,
    UserResponse, ChangePasswordRequest, TwoFactorVerifyRequest,
    LoginHistoryResponse, ActiveSessionResponse
)
from ..utils.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, verify_token, create_verification_token,
    create_password_reset_token, generate_2fa_secret, generate_2fa_qr_url,
    verify_2fa_code, generate_device_info
)
from ..utils.email import (
    send_verification_email,
    send_password_reset_email,
    send_password_reset_success_email,
    send_security_alert_email,
    send_login_alert_email,
    send_create_account_email,
)
from ..utils.otp_service import create_otp_expiry, generate_otp, hash_otp, is_otp_expired, verify_otp
from ..utils.dependencies import get_current_user, security
from ..utils.time import isoformat_utc_z
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

_rate_buckets = defaultdict(deque)

RESEND_COOLDOWN_SECONDS = 60


def _rate_limit(action: str, request_obj: FastAPIRequest, limit: int = 5, window_seconds: int = 60):
    """Simple in-memory per-IP rate limiter for auth endpoints.

    Disabled during testing (TESTING=true) to allow test suites to run
    without hitting artificial limits.
    """
    import os
    if os.getenv("TESTING", "").lower() in {"1", "true", "yes"}:
        return
    ip = request_obj.client.host if request_obj.client else "unknown"
    key = (action, ip)
    now = datetime.now(timezone.utc).timestamp()
    bucket = _rate_buckets[key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Please try again later.")
    bucket.append(now)


def _pack_email_otp(otp: str) -> str:
    """Store a hashed email OTP with its expiry in the existing token column."""
    return f"otp:{hash_otp(otp)}:{create_otp_expiry().isoformat()}"


def _verify_packed_email_otp(value: str, otp: str) -> bool:
    if not value or not value.startswith("otp:"):
        return False
    try:
        _, otp_hash, expires_raw = value.split(":", 2)
        expires_at = datetime.fromisoformat(expires_raw)
    except (ValueError, AttributeError):
        return False
    return not is_otp_expired(expires_at) and verify_otp(otp, otp_hash)


def _browser_from_user_agent(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if "edg" in ua or "edge" in ua:
        return "Edge"
    if "chrome" in ua:
        return "Chrome"
    if "firefox" in ua:
        return "Firefox"
    if "safari" in ua:
        return "Safari"
    return "Unknown"


def _send_login_alert(user: User, request_obj: FastAPIRequest) -> None:
    user_agent = request_obj.headers.get("user-agent", "")
    send_login_alert_email(
        user.email,
        isoformat_utc_z(utcnow_naive()),
        generate_device_info(user_agent),
        _browser_from_user_agent(user_agent),
        request_obj.client.host if request_obj.client else None,
        request_obj.headers.get("x-vercel-ip-city") or request_obj.headers.get("cf-ipcity"),
    )


def _create_session(db: Session, user: User, request_obj: FastAPIRequest, refresh_payload: dict = None) -> tuple[str, str]:
    ip_address = request_obj.client.host if request_obj.client else None
    user_agent = request_obj.headers.get("user-agent", "")
    refresh_payload = refresh_payload or {"sub": user.id, "sid": secrets.token_hex(16)}
    access_token = create_access_token({"sub": user.id, "sid": refresh_payload.get("sid")})
    refresh_token = create_refresh_token(refresh_payload)

    session = ActiveSession(
        user_id=user.id,
        token_jti=refresh_payload.get("sid"),
        ip_address=ip_address,
        user_agent=user_agent,
        device_info=generate_device_info(user_agent)
    )
    db.add(session)
    db.commit()
    return access_token, refresh_token


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, request_obj: FastAPIRequest, db: Session = Depends(get_db)):
    """Register a new user.

    - Validates password strength (8+ chars, uppercase, lowercase, digit)
    - Prevents duplicate email/username
    - Creates user, profile, and notification settings
    - Generates and stores a hashed 6-digit verification OTP (expires 10 min)
    - Sends ONE combined welcome + verification email
    - Does NOT create authenticated session or send login alert
    - Does NOT redirect to homepage; returns email_verification_required=true
    """
    _rate_limit("register", request_obj, limit=10, window_seconds=300)

    # Check duplicate email
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check duplicate username
    if db.query(User).filter(User.username == request.username.lower()).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create user
    user = User(
        email=request.email.lower(),
        username=request.username.lower(),
        hashed_password=hash_password(request.password),
        full_name=request.full_name
    )
    db.add(user)
    db.flush()

    # Create profile and notification settings
    profile = Profile(user_id=user.id)
    db.add(profile)
    notif_settings = NotificationSetting(user_id=user.id)
    db.add(notif_settings)

    # Generate and store verification OTP (hashed, 10-minute expiry)
    verification_otp = generate_otp()
    user.verification_token = _pack_email_otp(verification_otp)

    db.commit()
    db.refresh(user)

    # Send ONE combined welcome + verification email (not multiple duplicates)
    # Only send if SMTP is configured; if not, the service logs and continues
    send_create_account_email(user.email, user.username, verification_otp)

    # Return success with redirect to email verification page
    # Do NOT create authenticated session or send login alert
    # If EMAIL_VERIFICATION_REQUIRED is false, we still require verification
    email_required = settings.EMAIL_VERIFICATION_REQUIRED
    return {
        "message": "Account created successfully",
        "email_verification_required": True,
        "redirect": "/verify-email",
        "user_id": user.id
    }


@router.post("/verify-email")
def verify_email(
    request: VerifyEmailRequest,
    request_obj: FastAPIRequest,
    db: Session = Depends(get_db)
):
    """Verify email address using 6-digit OTP.

    - Accepts POST with {"token": "123456"}
    - OTP must be 6 digits, hashed-stored, checked with constant-time comparison
    - Expires after 10 minutes
    - Single-use: invalidated after successful verification
    - Rate-limited: 5 attempts per 60 seconds per IP
    """
    _rate_limit("verify-email", request_obj, limit=5, window_seconds=60)

    otp = request.token.strip()

    # Find user by iterating candidates with OTP-prefixed verification tokens
    candidates = db.query(User).filter(User.verification_token.like("otp:%")).all()
    user = next(
        (candidate for candidate in candidates
         if _verify_packed_email_otp(candidate.verification_token, otp)),
        None
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )

    if user.is_email_verified:
        return {"message": "Email already verified"}

    # Mark as verified and invalidate the OTP (single-use)
    user.is_email_verified = True
    user.verification_token = None
    db.commit()

    return {"message": "Email verified successfully", "redirect": "/login"}


@router.post("/resend-verification")
def resend_verification(
    request: ForgotPasswordRequest,
    request_obj: FastAPIRequest,
    db: Session = Depends(get_db)
):
    """Resend verification OTP.

    - 60-second cooldown between resends
    - Invalidates previous OTP and generates a new one
    - Rate-limited: 3 resend attempts per 300 seconds
    - Returns generic message to prevent email enumeration
    """
    _rate_limit("resend-verification", request_obj, limit=3, window_seconds=300)

    user = db.query(User).filter(User.email == request.email.lower()).first()
    if not user or user.is_email_verified:
        return {"message": "If the account exists, a verification code has been sent"}

    # Check cooldown on existing OTP
    if user.verification_token and user.verification_token.startswith("otp:"):
        try:
            _, _, expires_raw = user.verification_token.split(":", 2)
            expires_at = datetime.fromisoformat(expires_raw)
            # If current OTP is still valid (not expired), check cooldown
            if not is_otp_expired(expires_at):
                # A simple cooldown: if OTP was created less than RESEND_COOLDOWN_SECONDS ago
                created_at = expires_at - timedelta(minutes=10)
                if utcnow_naive() - created_at < timedelta(seconds=RESEND_COOLDOWN_SECONDS):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Please wait {RESEND_COOLDOWN_SECONDS} seconds before requesting a new code"
                    )
        except (ValueError, AttributeError):
            pass

    # Generate new OTP (invalidates previous one automatically)
    new_otp = generate_otp()
    user.verification_token = _pack_email_otp(new_otp)
    db.commit()

    send_create_account_email(user.email, user.username, new_otp)
    return {"message": "If the account exists, a verification code has been sent"}


@router.post("/login", response_model=Token)
def login(request: LoginRequest, request_obj: FastAPIRequest, db: Session = Depends(get_db)):
    """Login with email and password."""
    _rate_limit("login", request_obj, limit=5, window_seconds=60)
    user = db.query(User).filter(User.email == request.email.lower()).first()

    # Log the attempt
    ip_address = request_obj.client.host if request_obj.client else None
    user_agent = request_obj.headers.get("user-agent", "")

    if not user or not verify_password(request.password, user.hashed_password):
        if user:
            login_log = LoginHistory(
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                is_successful=False
            )
            db.add(login_log)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been banned"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Check email verification requirement
    if settings.EMAIL_VERIFICATION_REQUIRED and not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email before logging in."
        )

    # Check 2FA
    if user.two_factor_enabled:
        temp_token = create_access_token(
            {"sub": user.id, "purpose": "2fa_verification"},
            expires_delta=timedelta(minutes=5)
        )
        return {"access_token": temp_token, "refresh_token": "", "token_type": "bearer", "requires_2fa": True}

    # Update last login
    user.last_login = utcnow_naive()
    db.commit()

    # Log successful login
    login_log = LoginHistory(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        is_successful=True
    )
    db.add(login_log)

    access_token, refresh_token = _create_session(db, user, request_obj)
    _send_login_alert(user, request_obj)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/verify-2fa")
def verify_two_factor(
    request: TwoFactorVerifyRequest,
    request_obj: FastAPIRequest,
    db: Session = Depends(get_db)
):
    """Verify 2FA code during login."""
    _rate_limit("verify-2fa", request_obj, limit=5, window_seconds=60)
    if not request.temp_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="2FA token is required")
    payload = verify_token(request.temp_token, "access")
    if not payload or payload.get("purpose") != "2fa_verification":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired 2FA token")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.two_factor_enabled or not user.two_factor_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled")
    if not verify_2fa_code(user.two_factor_secret, request.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")
    user.last_login = utcnow_naive()
    db.add(LoginHistory(user_id=user.id, ip_address=request_obj.client.host if request_obj.client else None, user_agent=request_obj.headers.get("user-agent", ""), is_successful=True))
    access_token, refresh_token = _create_session(db, user, request_obj)
    _send_login_alert(user, request_obj)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
def refresh_token(request: RefreshTokenRequest, request_obj: FastAPIRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    payload = verify_token(request.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    user_id = payload.get("sub")
    sid = payload.get("sid")
    if not sid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh session")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or banned"
        )

    session = db.query(ActiveSession).filter(
        ActiveSession.user_id == user.id,
        ActiveSession.token_jti == sid,
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")

    # Rotate refresh token/session identifier
    db.delete(session)
    access_token, new_refresh_token = _create_session(db, user, request_obj)

    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, request_obj: FastAPIRequest, db: Session = Depends(get_db)):
    """Send password reset OTP.

    - Always returns the same generic message regardless of whether email exists
    - Generates a secure 6-digit OTP, stores only its hash
    - Expires after 10 minutes
    - Invalidates any previous reset OTP
    - Does NOT reveal whether the email exists
    """
    _rate_limit("forgot-password", request_obj, limit=3, window_seconds=300)

    user = db.query(User).filter(User.email == request.email.lower()).first()

    if user:
        # Generate OTP, invalidate previous one
        reset_otp = generate_otp()
        user.reset_token = hash_otp(reset_otp)
        user.reset_token_expires = create_otp_expiry()
        db.commit()

        send_password_reset_email(user.email, reset_otp)

    # Return generic message regardless
    return {
        "message": "If an account exists for this email, a password reset OTP has been sent.",
        "redirect": "/reset-password"
    }


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, request_obj: FastAPIRequest, db: Session = Depends(get_db)):
    """Reset password using 6-digit OTP.

    Accepts: {"token": "123456", "password": "NewPass123"}
    - Validates OTP: 6-digit, hashed, not expired, not already used
    - Applies same strong-password rules as registration
    - On success:
      - Invalidates the OTP (single-use)
      - Revokes all active sessions
      - Sends password-change confirmation email
      - Returns redirect to login
    """
    _rate_limit("reset-password", request_obj, limit=5, window_seconds=300)

    otp = request.token.strip()
    password = request.password

    # Find user by iterating candidates with non-null reset_token
    candidates = db.query(User).filter(User.reset_token.isnot(None)).all()
    user = next(
        (candidate for candidate in candidates
         if verify_otp(otp, candidate.reset_token)),
        None
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )

    # Check expiry
    if not user.reset_token_expires or user.reset_token_expires < utcnow_naive():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset code has expired. Please request a new one."
        )

    # OTP already used (token cleared) - should not happen since we check user above,
    # but double-check for security
    if user.reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset code has already been used."
        )

    # Update password
    user.hashed_password = hash_password(password)
    # Invalidate OTP (single-use)
    user.reset_token = None
    user.reset_token_expires = None

    # Revoke all active sessions
    db.query(ActiveSession).filter(ActiveSession.user_id == user.id).delete()

    db.commit()

    # Send password-change confirmation email
    send_password_reset_success_email(user.email)

    return {"message": "Password reset successfully", "redirect": "/login"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return current_user


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password."""
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    current_user.hashed_password = hash_password(request.new_password)
    db.commit()
    send_security_alert_email(
        current_user.email,
        "Password changed on your account",
        "Your SocialHub password was changed from an authenticated session. If this was not you, contact support immediately.",
    )

    return {"message": "Password changed successfully"}


@router.post("/setup-2fa")
def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Setup two-factor authentication."""
    secret = generate_2fa_secret()
    qr_url = generate_2fa_qr_url(current_user.username, secret)

    current_user.two_factor_secret = secret
    db.commit()

    return {"secret": secret, "qr_code_url": qr_url}


@router.post("/enable-2fa")
def enable_2fa(
    request: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable 2FA after verifying setup code."""
    if not current_user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please set up 2FA first"
        )

    if not verify_2fa_code(current_user.two_factor_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )

    current_user.two_factor_enabled = True
    db.commit()

    return {"message": "2FA enabled successfully"}


@router.post("/disable-2fa")
def disable_2fa(
    request: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable 2FA."""
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )

    if not verify_2fa_code(current_user.two_factor_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )

    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    db.commit()

    return {"message": "2FA disabled successfully"}


@router.get("/login-history")
def get_login_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get login history for current user."""
    history = db.query(LoginHistory).filter(
        LoginHistory.user_id == current_user.id
    ).order_by(LoginHistory.login_at.desc()).limit(20).all()
    return [{"id": h.id, "ip_address": h.ip_address, "user_agent": h.user_agent,
             "login_at": isoformat_utc_z(h.login_at),
             "is_successful": h.is_successful} for h in history]


@router.get("/active-sessions")
def get_active_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active sessions for current user."""
    sessions = db.query(ActiveSession).filter(
        ActiveSession.user_id == current_user.id
    ).order_by(ActiveSession.last_activity.desc()).all()
    return [{"id": s.id, "ip_address": s.ip_address, "user_agent": s.user_agent,
             "device_info": s.device_info,
             "last_activity": isoformat_utc_z(s.last_activity),
             "created_at": isoformat_utc_z(s.created_at)} for s in sessions]


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an active session."""
    session = db.query(ActiveSession).filter(
        ActiveSession.id == session_id,
        ActiveSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()

    return {"message": "Session revoked successfully"}


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Logout current device by revoking the active JWT session when available."""
    payload = verify_token(credentials.credentials, "access") if credentials else None
    sid = payload.get("sid") if payload else None
    if sid:
        db.query(ActiveSession).filter(
            ActiveSession.user_id == current_user.id,
            ActiveSession.token_jti == sid,
        ).delete()
        db.commit()
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
def logout_all_devices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout from all devices by revoking every refresh session."""
    db.query(ActiveSession).filter(ActiveSession.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Logged out from all devices successfully"}