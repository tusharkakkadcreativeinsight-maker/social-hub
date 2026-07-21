from typing import Optional
import os
import secrets
from dotenv import load_dotenv

# Load .env from the project root (SocialHub/.env) regardless of cwd.
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.abspath(os.path.join(backend_dir, ".."))
dotenv_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path)

# Also support the common local layout where developers keep secrets in
# SocialHub/backend/.env. Values already loaded from SocialHub/.env or the
# process environment keep priority; backend/.env fills in missing values.
backend_dotenv_path = os.path.join(backend_dir, ".env")
load_dotenv(backend_dotenv_path, override=False)


def _sqlite_url(path: str, async_driver: bool = False) -> str:
    """Build an absolute SQLite URL so every entrypoint uses one DB file."""
    normalized = os.path.abspath(path).replace("\\", "/")
    prefix = "sqlite+aiosqlite" if async_driver else "sqlite"
    return f"{prefix}:///{normalized}"


def _postgres_url(raw_url: str, async_driver: bool = False) -> str:
    """Normalize PostgreSQL URLs for SQLAlchemy sync/async engines."""
    if async_driver:
        if raw_url.startswith("postgresql+asyncpg://"):
            return raw_url
        if raw_url.startswith("postgresql+psycopg2://"):
            return raw_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        if raw_url.startswith("postgresql://"):
            return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if raw_url.startswith("postgres://"):
            return raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    else:
        if raw_url.startswith("postgresql+asyncpg://"):
            return raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        if raw_url.startswith("postgres://"):
            return raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
        if raw_url.startswith("postgresql://"):
            return raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return raw_url


def _resolve_database_url(raw_url: Optional[str], async_driver: bool = False) -> str:
    """Resolve database URLs for SQLite and PostgreSQL.

    Old project scripts were sometimes run from the repository root and
    sometimes from backend/, which created multiple socialhub.db files. This
    keeps SQLite on a single project-root database while preserving explicit
    absolute SQLite paths. PostgreSQL URLs are normalized to the correct
    SQLAlchemy sync/async drivers.
    """
    default_path = os.path.join(project_root, "socialhub.db")
    if not raw_url:
        return _sqlite_url(default_path, async_driver)

    if raw_url.startswith(("postgresql://", "postgresql+psycopg2://", "postgresql+asyncpg://", "postgres://")):
        return _postgres_url(raw_url, async_driver)

    if async_driver and raw_url.startswith("sqlite:///"):
        raw_url = raw_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if not async_driver and raw_url.startswith("sqlite+aiosqlite:///"):
        raw_url = raw_url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)

    if raw_url.startswith("sqlite:///./") or raw_url in {"sqlite:///socialhub.db", "sqlite:///./socialhub.db"}:
        return _sqlite_url(default_path, async_driver)
    if raw_url.startswith("sqlite+aiosqlite:///./") or raw_url in {"sqlite+aiosqlite:///socialhub.db", "sqlite+aiosqlite:///./socialhub.db"}:
        return _sqlite_url(default_path, True)
    if raw_url.startswith("sqlite:///") and not raw_url.startswith("sqlite:////"):
        db_path = raw_url.replace("sqlite:///", "", 1)
        if not os.path.isabs(db_path):
            return _sqlite_url(os.path.join(project_root, db_path), async_driver)
    if raw_url.startswith("sqlite+aiosqlite:///") and not raw_url.startswith("sqlite+aiosqlite:////"):
        db_path = raw_url.replace("sqlite+aiosqlite:///", "", 1)
        if not os.path.isabs(db_path):
            return _sqlite_url(os.path.join(project_root, db_path), True)
    return raw_url


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _parse_cors_origins(raw: Optional[str], debug: bool) -> list:
    """Parse CORS origins from .env.

    Local development remains beginner-friendly. Production must explicitly set
    trusted origins and never falls back to '*'.
    """
    if not raw:
        if debug:
            return ["*"]
        raise RuntimeError("CORS_ORIGINS must be set to trusted origins when DEBUG=false")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins or (not debug and "*" in origins):
        raise RuntimeError("CORS_ORIGINS cannot be empty or '*' when DEBUG=false")
    return origins


def _load_secret_key(debug: bool) -> str:
    """Load JWT secret safely.

    Development gets an ephemeral key if none is provided. Production requires a
    strong explicit SECRET_KEY and refuses known placeholder defaults.
    """
    value = os.getenv("SECRET_KEY", "").strip()
    unsafe = {
        "",
        "super-secret-key-change-in-production",
        "change-this-secret-key",
        "change-me",
        "your-secret-key-here",
    }
    if debug:
        return value or secrets.token_urlsafe(48)
    if value in unsafe or len(value) < 32:
        raise RuntimeError("Set a strong SECRET_KEY (32+ chars) before running with DEBUG=false")
    return value


class Settings:
    # App
    APP_NAME: str = "SocialHub"
    DEBUG: bool = _env_bool("DEBUG", True)
    VERSION: str = "1.0.0"

    # Database (single project-root SQLite DB by default; PostgreSQL-ready)
    DATABASE_URL: str = _resolve_database_url(os.getenv("DATABASE_URL"), async_driver=False)
    DATABASE_URL_ASYNC: str = _resolve_database_url(os.getenv("DATABASE_URL_ASYNC") or os.getenv("DATABASE_URL"), async_driver=True)

    # JWT
    SECRET_KEY: str = _load_secret_key(DEBUG)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Email (disabled by default, configure SMTP for production). EMAIL_* is
    # preferred; SMTP_* aliases are kept for backward compatibility.
    EMAIL_HOST: str = os.getenv("EMAIL_HOST", os.getenv("SMTP_HOST", ""))
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", os.getenv("SMTP_PORT", "587")))
    EMAIL_USER: str = os.getenv("EMAIL_USER", os.getenv("SMTP_USER", ""))
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", os.getenv("SMTP_PASSWORD", ""))
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", os.getenv("EMAIL_FROM_ADDRESS", os.getenv("EMAIL_USER", "noreply@socialhub.com")))
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "SocialHub Security")
    EMAIL_REPLY_TO: str = os.getenv("EMAIL_REPLY_TO", "support@socialhub.com")
    SUPPORT_EMAIL: str = os.getenv("SUPPORT_EMAIL", "support@socialhub.com")
    SMTP_HOST: str = EMAIL_HOST
    SMTP_PORT: int = EMAIL_PORT
    SMTP_USER: str = EMAIL_USER
    SMTP_PASSWORD: str = EMAIL_PASSWORD

    # Upload
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))
    MAX_IMAGE_SIZE: int = int(os.getenv("MAX_IMAGE_SIZE", str(10 * 1024 * 1024)))
    MAX_VIDEO_SIZE: int = int(os.getenv("MAX_VIDEO_SIZE", str(100 * 1024 * 1024)))
    ALLOWED_EXTENSIONS: list = [ext.strip().lower() for ext in os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,gif,webp,mp4,webm,mov,mp3,wav,m4a,ogg").split(",") if ext.strip()]

    # Get absolute path for uploads. Tests may override this with UPLOAD_DIR so
    # uploaded files never touch the real frontend/uploads directory.
    _base_dir: str = project_root
    UPLOAD_DIR: str = os.path.abspath(os.getenv("UPLOAD_DIR", os.path.join(_base_dir, "frontend", "uploads")))

    # CORS
    CORS_ORIGINS: list = _parse_cors_origins(os.getenv("CORS_ORIGINS") or os.getenv("ALLOWED_ORIGINS"), DEBUG)

    # Story
    STORY_DURATION_HOURS: int = 24

    # Redis
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "")

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Rate limiting
    RATE_LIMIT_LOGIN: str = os.getenv("RATE_LIMIT_LOGIN", "5/minute")
    RATE_LIMIT_API: str = os.getenv("RATE_LIMIT_API", "100/minute")

    # Chat
    MAX_CHAT_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_CHAT_EXTENSIONS: list = ["jpg", "jpeg", "png", "gif", "webp", "mp4", "webm", "mov", "pdf", "doc", "docx", "txt"]

    # AI Chat (optional; leave OPENAI_API_KEY empty to use local fallback replies)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # 2FA
    TWO_FACTOR_ENABLED: bool = os.getenv("TWO_FACTOR_ENABLED", "false").lower() == "true"
    SEED_DEMO_ACCOUNTS: bool = _env_bool("SEED_DEMO_ACCOUNTS", False)
    AUTO_CREATE_TABLES: bool = _env_bool("AUTO_CREATE_TABLES", DEBUG)
    AUTO_SCHEMA_COMPATIBILITY: bool = _env_bool("AUTO_SCHEMA_COMPATIBILITY", False)

    # Email verification
    EMAIL_VERIFICATION_REQUIRED: bool = os.getenv("EMAIL_VERIFICATION_REQUIRED", "false").lower() == "true"

    # App URL (for emails)
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")

    # Official Meta / Instagram Graph API OAuth. Never hardcode these values.
    INSTAGRAM_CLIENT_ID: str = os.getenv("INSTAGRAM_CLIENT_ID", "")
    INSTAGRAM_CLIENT_SECRET: str = os.getenv("INSTAGRAM_CLIENT_SECRET", "")
    INSTAGRAM_REDIRECT_URI: str = os.getenv("INSTAGRAM_REDIRECT_URI", "http://localhost:8000/api/instagram/callback")
    INSTAGRAM_GRAPH_VERSION: str = os.getenv("INSTAGRAM_GRAPH_VERSION", os.getenv("GRAPH_VERSION", "v19.0"))
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", os.getenv("SECRET_KEY", "change-this-app-secret-key"))

    def get_profile_pics_dir(self):
        return os.path.join(self.UPLOAD_DIR, "profiles")

    def get_cover_photos_dir(self):
        return os.path.join(self.UPLOAD_DIR, "covers")

    def get_post_images_dir(self):
        return os.path.join(self.UPLOAD_DIR, "posts")

    def get_videos_dir(self):
        return os.path.join(self.UPLOAD_DIR, "posts")

    def get_reels_dir(self):
        return os.path.join(self.UPLOAD_DIR, "reels")

    def get_stories_dir(self):
        return os.path.join(self.UPLOAD_DIR, "stories")

    def get_music_dir(self):
        return os.path.join(self.UPLOAD_DIR, "music")


settings = Settings()