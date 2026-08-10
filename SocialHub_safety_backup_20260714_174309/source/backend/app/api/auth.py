from fastapi import APIRouter, Depends, HTTPException, status, Request as FastAPIRequest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
import secrets

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
from ..utils.email import send_verification_email, send_password_reset_email, send_welcome_email
from ..utils.dependencies import get_current_user, security
from ..utils.time import isoformat_utc_z

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

_rate_buckets = defaultdict(deque)


def _rate_limit(action: str, request_obj: FastAPIRequest, limit: int = 5, window_seconds: int = 60):
    """Simple in-memory per-IP rate limiter for auth endpoints.

    This is intentionally dependency-free for local SQLite mode. In production,
    place the app behind a reverse proxy and replace this with Redis-backed
    limiting when horizontally scaling.
    """
    ip = request_obj.client.host if request_obj.client else "unknown"
    key = (action, ip)
    now = datetime.now(timezone.utc).timestamp()
    bucket = _rate_buckets[key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Please try again later.")
    bucket.append(now)


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


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, request_obj: FastAPIRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    _rate_limit("register", request_obj, limit=10, window_seconds=300)
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if db.query(User).filter(User.username == request.username.lower()).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    user = User(
        email=request.email.lower(),
        username=request.username.lower(),
        hashed_password=hash_password(request.password),
        full_name=request.full_name
    )
    db.add(user)
    db.flush()

    profile = Profile(user_id=user.id)
    db.add(profile)

    # Create default notification settings
    notif_settings = NotificationSetting(user_id=user.id)
    db.add(notif_settings)

    db.commit()
    db.refresh(user)

    # Send emails (non-blocking, ignore failures)
    send_welcome_email(user.email, user.username)

    verification_token = create_verification_token(user.email)
    user.verification_token = verification_token
    db.commit()
    send_verification_email(user.email, verification_token)

    access_token, refresh_token = _create_session(db, user, request_obj)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=Token)
def login(request: LoginRequest, request_obj: FastAPIRequest, db: Session = Depends(get_db)):
    """Login with email and password."""
    _rate_limit("login", request_obj, limit=5, window_seconds=60)
    user = db.query(User).filter(User.email == request.email.lower()).first()

    # Log the attempt
    ip_address = request_obj.client.host if request_obj.client else None
    user_agent = request_obj.headers.get("user-agent", "")

    if not user or not verify_password(request.password, user.hashed_password):
        # Log failed attempt
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

    # Check 2FA
    if user.two_factor_enabled:
        # Return a temporary token for 2FA verification
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

    # Rotate refresh token/session identifier to make replayed refresh tokens unusable.
    db.delete(session)
    access_token, new_refresh_token = _create_session(db, user, request_obj)

    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify email address with token."""
    # First try to find by verification_token field
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token is required"
        )

    user = db.query(User).filter(User.verification_token == token).first()
    if user:
        user.is_email_verified = True
        user.verification_token = None
        db.commit()
        return {"message": "Email verified successfully"}

    # Try JWT-based verification
    payload = verify_token(token, "access")
    if payload and payload.get("purpose") == "email_verification":
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if user:
            if user.is_email_verified:
                return {"message": "Email already verified"}
            user.is_email_verified = True
            user.verification_token = None
            db.commit()
            return {"message": "Email verified successfully"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired verification token"
    )


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, request_obj: FastAPIRequest, db: Session = Depends(get_db)):
    """Send password reset email."""
    _rate_limit("forgot-password", request_obj, limit=5, window_seconds=300)
    user = db.query(User).filter(User.email == request.email.lower()).first()
    if not user:
        return {"message": "If the email exists, a reset link has been sent"}

    reset_token = create_password_reset_token(user.email)
    user.reset_token = reset_token
    user.reset_token_expires = utcnow_naive() + timedelta(hours=1)
    db.commit()

    send_password_reset_email(user.email, reset_token)
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, request_obj: FastAPIRequest, db: Session = Depends(get_db)):
    """Reset password with token."""
    _rate_limit("reset-password", request_obj, limit=5, window_seconds=300)
    # First try by stored reset_token
    if request.token:
        user = db.query(User).filter(User.reset_token == request.token).first()
        if user:
            if not user.reset_token_expires or user.reset_token_expires < utcnow_naive():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
            user.hashed_password = hash_password(request.password)
            user.reset_token = None
            user.reset_token_expires = None
            db.query(ActiveSession).filter(ActiveSession.user_id == user.id).delete()
            db.commit()
            return {"message": "Password reset successfully"}

    # Try JWT-based reset
    payload = verify_token(request.token, "access")
    if payload and payload.get("purpose") == "password_reset":
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if user:
            if user.reset_token != request.token or not user.reset_token_expires or user.reset_token_expires < utcnow_naive():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
            user.hashed_password = hash_password(request.password)
            user.reset_token = None
            user.reset_token_expires = None
            db.query(ActiveSession).filter(ActiveSession.user_id == user.id).delete()
            db.commit()
            return {"message": "Password reset successfully"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token"
    )


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