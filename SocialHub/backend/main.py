import os
import sys
from fastapi import FastAPI, WebSocket, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import logging
import subprocess
import importlib.util
from sqlalchemy import text

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import engine, Base, SessionLocal
# Import models to register them with Base.metadata
from app.models import models  # noqa: F401
from app.api import (
    auth_router, users_router, posts_router, likes_router,
    comments_router, followers_router, stories_router, reels_router,
    messaging_router, notifications_router, search_router,
    reports_router, admin_router, trending_router, instagram_router, ai_chat_router
    , aliases_router, translate_router, media_studio_router,
    verification_router, collections_router, analytics_router,
    wallet_router, highlights_router, hashtags_router, music_router, live_router
)
from app.api.data_studio import router as data_studio_router
from app.api.advanced import router as advanced_router

from app.websocket.chat import handle_chat_websocket
from app.websocket.live import handle_live_websocket


# Load environment variables
load_dotenv()

# Configure logging
if settings.DEBUG:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="SocialHub - A complete social media platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )


# Paths
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
static_dir = os.path.join(frontend_dir, "static")
uploads_dir = settings.UPLOAD_DIR
templates_dir = os.path.join(frontend_dir, "templates")
templates = Jinja2Templates(directory=templates_dir)

# Create directories if they don't exist
os.makedirs(static_dir, exist_ok=True)
os.makedirs(uploads_dir, exist_ok=True)
for upload_subdir in (
    "posts", "reels", "stories", "profiles", "covers", "music",
    "marketplace", "original_media", "chat", "live"
):
    os.makedirs(os.path.join(uploads_dir, upload_subdir), exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


def serve_html(request: Request, filename: str, **context):
    """Render a frontend template with Jinja2.

    Most SocialHub pages are complete HTML documents, while newer shared pages
    use `{% extends "base.html" %}`. Rendering every page through Jinja keeps a
    single consistent frontend delivery path and prevents raw Jinja syntax from
    appearing in the browser.
    """
    filepath = os.path.join(templates_dir, filename)
    if not os.path.exists(filepath):
        logger.warning("Frontend template missing: %s", filename)
        return JSONResponse(status_code=404, content={"detail": f"Template {filename} not found"})
    return templates.TemplateResponse(request, filename, context)


# ==================== API Routes ====================
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(posts_router)
app.include_router(likes_router)
app.include_router(comments_router)
app.include_router(followers_router)
app.include_router(stories_router)
app.include_router(reels_router)
app.include_router(messaging_router)
app.include_router(notifications_router)
app.include_router(search_router)
app.include_router(reports_router)
app.include_router(admin_router)
app.include_router(trending_router)
app.include_router(instagram_router)
app.include_router(ai_chat_router)
app.include_router(aliases_router)
app.include_router(translate_router)
app.include_router(data_studio_router, prefix="/api/data-studio")
app.include_router(advanced_router)
app.include_router(media_studio_router)
app.include_router(verification_router)
app.include_router(collections_router)
app.include_router(analytics_router)
app.include_router(wallet_router)
app.include_router(highlights_router)
app.include_router(hashtags_router)
app.include_router(music_router)
app.include_router(live_router)

# ==================== Health Check ====================


@app.get("/api/health")
@app.get("/health")
def health_check():
    """Return a small, non-sensitive runtime health payload.

    The endpoint intentionally avoids exposing stack traces, database URLs, or
    environment details. It only verifies that SQLAlchemy can execute a trivial
    statement against the configured database.
    """
    database_status = "disconnected"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        logger.warning("Health check database connectivity failed", exc_info=False)

    return {
        "success": database_status == "connected",
        "status": "healthy" if database_status == "connected" else "degraded",
        "database": database_status,
    }


# ==================== WebSocket Endpoint ====================
@app.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket endpoint for real-time chat."""
    await handle_chat_websocket(websocket, token)


@app.websocket("/ws/live/{live_id}")
async def websocket_live_endpoint(websocket: WebSocket, live_id: str, token: str = Query(...)):
    """WebSocket endpoint for live room simulation and future WebRTC signaling."""
    await handle_live_websocket(websocket, live_id, token)


# ==================== Frontend Routes ====================
@app.get("/")
async def serve_index(request: Request):
    return serve_html(request, "index.html")


@app.get("/login")
async def serve_login(request: Request):
    return serve_html(request, "login.html")


@app.get("/register")
async def serve_register(request: Request):
    return serve_html(request, "register.html")


@app.get("/profile/{username}")
async def serve_profile(request: Request, username: str):
    return serve_html(request, "profile.html", username=username)


@app.get("/posts")
async def serve_posts(request: Request):
    return serve_html(request, "posts.html")


@app.get("/chat")
async def serve_chat(request: Request):
    return serve_html(request, "chat.html")


@app.get("/chat/{chat_id}")
async def serve_chat_room(request: Request, chat_id: str):
    return serve_html(request, "chat.html", chat_id=chat_id)


@app.get("/stories")
async def serve_stories(request: Request):
    return serve_html(request, "stories.html")


@app.get("/reels")
async def serve_reels(request: Request):
    return serve_html(request, "reels.html")


@app.get("/notifications")
async def serve_notifications(request: Request):
    return serve_html(request, "notifications.html")


@app.get("/search")
async def serve_search(request: Request):
    return serve_html(request, "search.html")


@app.get("/admin")
async def serve_admin(request: Request):
    return serve_html(request, "admin.html")


@app.get("/verify-email")
async def serve_verify_email(request: Request):
    return serve_html(request, "verify_email.html")


@app.get("/forgot-password")
async def serve_forgot_password(request: Request):
    return serve_html(request, "forgot_password.html")


@app.get("/reset-password")
async def serve_reset_password(request: Request, token: str = ""):
    return serve_html(request, "reset_password.html", token=token)


@app.get("/explore")
async def serve_explore(request: Request):
    return serve_html(request, "explore.html")


@app.get("/bookmarks")
async def serve_bookmarks(request: Request):
    return serve_html(request, "posts.html")


@app.get("/edit-profile")
async def serve_edit_profile(request: Request):
    return serve_html(request, "profile.html")


@app.get("/settings")
async def serve_settings(request: Request):
    return serve_html(request, "settings.html")


@app.get("/instagram-studio")
async def serve_instagram_studio(request: Request):
    return serve_html(request, "instagram_studio.html")


@app.get("/connect-instagram")
async def serve_connect_instagram(request: Request):
    return serve_html(request, "connect_instagram.html")


@app.get("/data-studio")
async def serve_data_studio(request: Request):
    return serve_html(request, "data_studio.html")


@app.get("/creator-dashboard")
async def serve_creator_dashboard(request: Request):
    return serve_html(request, "creator_dashboard.html")


@app.get("/scheduled")
async def serve_scheduled_posts(request: Request):
    return serve_html(request, "scheduled.html")


@app.get("/marketplace")
async def serve_marketplace(request: Request):
    return serve_html(request, "marketplace.html")


@app.get("/collabs")
async def serve_collabs(request: Request):
    return serve_html(request, "collabs.html")


@app.get("/wallet")
async def serve_wallet(request: Request):
    return serve_html(request, "wallet.html")


@app.get("/saved")
async def serve_saved(request: Request):
    return serve_html(request, "saved.html")


@app.get("/verification")
async def serve_verification(request: Request):
    return serve_html(request, "verification.html")


@app.get("/follow-requests")
async def serve_follow_requests(request: Request):
    return serve_html(request, "follow_requests.html")


@app.get("/hashtag/{tag}")
async def serve_hashtag(request: Request, tag: str):
    return serve_html(request, "hashtag.html", hashtag=tag, tag=tag)


@app.get("/ai-creator-studio")
async def serve_ai_creator_studio(request: Request):
    return serve_html(request, "ai_creator_studio.html")


@app.get("/music-library")
async def serve_music_library(request: Request):
    return serve_html(request, "music_library.html")


@app.get("/live")
async def serve_live(request: Request):
    return serve_html(request, "live.html")


@app.get("/collections")
async def serve_collections(request: Request):
    return serve_html(request, "collections.html")




@app.get("/offline")
async def serve_offline(request: Request):
    return serve_html(request, "offline.html")




@app.get("/two-factor")
async def serve_two_factor(request: Request):
    return serve_html(request, "two_factor.html")

@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse(os.path.join(static_dir, "manifest.json"), media_type="application/manifest+json")


@app.get("/service-worker.js")
async def serve_service_worker():
    return FileResponse(os.path.join(static_dir, "service-worker.js"), media_type="application/javascript")


# ==================== Startup Event ====================
def ensure_demo_accounts():
    """Create/update local demo users required by smoke tests and UI demos."""
    if not (settings.DEBUG or settings.SEED_DEMO_ACCOUNTS):
        logger.info("Demo account seeding skipped (DEBUG=false and SEED_DEMO_ACCOUNTS=false)")
        return
    from app.models.models import User, Profile, NotificationSetting, Post
    from app.utils.security import hash_password
    db = SessionLocal()
    try:
        demo_accounts = [
            {
                "email": "test@test.com",
                "username": "testuser",
                "password": "TestPass1",
                "full_name": "Test User",
                "role": "user",
            },
        ]

        for account in demo_accounts:
            user = db.query(User).filter(User.email == account["email"]).first()
            if not user:
                user = db.query(User).filter(User.username == account["username"]).first()
            if not user:
                user = User(
                    email=account["email"],
                    username=account["username"],
                    hashed_password=hash_password(account["password"]),
                    full_name=account["full_name"],
                    role=account["role"],
                    is_active=True,
                    is_banned=False,
                    is_email_verified=True,
                )
                db.add(user)
                db.flush()
            else:
                # Do not reset passwords for existing accounts on startup.
                user.email = account["email"]
                user.username = account["username"]
                user.full_name = user.full_name or account["full_name"]
                user.role = user.role or account["role"]
                user.is_active = True
                user.is_banned = False
                user.is_email_verified = True

            if not db.query(Profile).filter(Profile.user_id == user.id).first():
                db.add(Profile(user_id=user.id, bio="Local SocialHub demo account"))
            if not db.query(NotificationSetting).filter(NotificationSetting.user_id == user.id).first():
                db.add(NotificationSetting(user_id=user.id))
            if db.query(Post).filter(Post.user_id == user.id, Post.is_deleted == False).count() == 0:
                db.add(Post(
                    user_id=user.id,
                    content=f"Welcome to SocialHub from @{account['username']}!",
                    hashtags=["demo", "socialhub"],
                    is_published=True,
                    post_type="normal",
                ))

        db.commit()
        logger.info("Demo accounts ensured")
    except Exception as exc:
        db.rollback()
        logger.warning(f"Could not ensure demo accounts: {exc}")
    finally:
        db.close()


def ensure_schema_compatibility():
    """Add newly introduced SQLite columns when an older local DB already exists."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    import sqlite3

    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    migrations = {
        "profiles": {
            "profile_picture": "VARCHAR(500) DEFAULT 'default_profile.png'",
            "cover_photo": "VARCHAR(500) DEFAULT 'default_cover.jpg'",
        },
        "posts": {
            "is_deleted": "BOOLEAN DEFAULT 0 NOT NULL",
            "deleted_at": "DATETIME",
        },
        "comments": {
            "is_deleted": "BOOLEAN DEFAULT 0 NOT NULL",
            "deleted_at": "DATETIME",
        },
        "reels": {
            "is_deleted": "BOOLEAN DEFAULT 0 NOT NULL",
            "deleted_at": "DATETIME",
            "edit_metadata": "TEXT",
            "trim_start": "FLOAT",
            "trim_end": "FLOAT",
            "text_overlay": "VARCHAR(255)",
            "filter_name": "VARCHAR(100)",
            "music_name": "VARCHAR(150)",
            "audio_name": "VARCHAR(150)",
            "location": "VARCHAR(255)",
            "cover_image": "VARCHAR(500)",
            "visibility": "VARCHAR(20) DEFAULT 'public' NOT NULL",
            "music_id": "VARCHAR",
        },
        "music": {
            "created_by": "VARCHAR",
            "use_count": "INTEGER DEFAULT 0 NOT NULL",
            "updated_at": "DATETIME",
        },
        "reel_comments": {
            "parent_id": "VARCHAR",
            "likes_count": "INTEGER DEFAULT 0 NOT NULL",
        },
        "scheduled_posts": {
            "content_type": "VARCHAR(20) DEFAULT 'post' NOT NULL",
            "platform": "VARCHAR(20) DEFAULT 'socialhub' NOT NULL",
            "published_at": "DATETIME",
        },
        "stories": {
            "is_deleted": "BOOLEAN DEFAULT 0 NOT NULL",
            "deleted_at": "DATETIME",
            "is_archived": "BOOLEAN DEFAULT 0 NOT NULL",
        },
        "messages": {
            "receiver_id": "VARCHAR",
            "message_text": "TEXT",
            "is_deleted": "BOOLEAN DEFAULT 0 NOT NULL",
            "deleted_at": "DATETIME",
            "deleted_for_all": "BOOLEAN DEFAULT 0 NOT NULL",
            "updated_at": "DATETIME",
        },
        "live_streams": {
            "status": "VARCHAR(20) DEFAULT 'active' NOT NULL",
            "camera_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "microphone_enabled": "BOOLEAN DEFAULT 1 NOT NULL",
            "viewer_count": "INTEGER DEFAULT 0 NOT NULL",
            "likes_count": "INTEGER DEFAULT 0 NOT NULL",
            "gifts_count": "INTEGER DEFAULT 0 NOT NULL",
            "is_deleted": "BOOLEAN DEFAULT 0 NOT NULL",
            "deleted_at": "DATETIME",
            "started_at": "DATETIME",
            "ended_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "marketplace_products": {
            "is_deleted": "BOOLEAN DEFAULT 0 NOT NULL",
            "updated_at": "DATETIME",
        },
        "collaboration_offers": {
            "status": "VARCHAR(20) DEFAULT 'open' NOT NULL",
            "updated_at": "DATETIME",
        },
        "original_media_assets": {
            "is_used_in_post": "BOOLEAN DEFAULT 0 NOT NULL",
            "is_used_in_reel": "BOOLEAN DEFAULT 0 NOT NULL",
            "ownership_confirmed": "BOOLEAN DEFAULT 0 NOT NULL",
        },
        "demo_data_batches": {
            "is_deleted": "BOOLEAN DEFAULT 0 NOT NULL",
            "deleted_at": "DATETIME",
        },
        "reports": {
            "reel_id": "VARCHAR",
            "story_id": "VARCHAR",
            "resolved_by": "VARCHAR",
            "resolved_at": "DATETIME",
        },
        "audit_logs": {
            "reason": "TEXT",
        },
    }
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        for table, columns in migrations.items():
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cur.fetchone():
                continue
            cur.execute(f"PRAGMA table_info({table})")
            existing = {row[1] for row in cur.fetchall()}
            for column, ddl in columns.items():
                if column not in existing:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        conn.commit()
    finally:
        conn.close()


def normalize_existing_upload_paths():
    """Normalize old DB media paths to clean paths relative to frontend/uploads.

    Older local databases may contain absolute Windows paths, /uploads/... URLs,
    or duplicated uploads/uploads prefixes. New uploads already use clean values
    like posts/file.png, reels/file.mp4, stories/file.png, profiles/file.png,
    and covers/file.png. This startup repair keeps old media accessible without
    deleting rows or files.
    """
    from app.models.models import PostImage, Reel, Story, Profile, MarketplaceProduct

    if not (settings.DEBUG or settings.AUTO_CREATE_TABLES):
        return

    base_upload_dir = os.path.abspath(settings.UPLOAD_DIR).replace("\\", "/")

    def clean_path(value):
        if not value or str(value).startswith(("http://", "https://", "default")):
            return value
        raw = str(value).strip().replace("\\", "/")
        lower = raw.lower()
        marker = "/uploads/"
        if marker in lower:
            raw = raw[lower.rfind(marker) + len(marker):]
        elif lower.startswith("uploads/"):
            raw = raw[len("uploads/"):]
        elif lower.startswith(base_upload_dir.lower().rstrip("/") + "/"):
            raw = raw[len(base_upload_dir.rstrip("/")) + 1:]
        raw = raw.lstrip("/")
        while raw.lower().startswith("uploads/"):
            raw = raw[len("uploads/"):]

        legacy_prefixes = {
            "post_images/": "posts/",
            "videos/": "posts/",
            "profile_pics/": "profiles/",
            "cover_photos/": "covers/",
            "chat_files/": "chat/",
        }
        for old, new in legacy_prefixes.items():
            if raw.lower().startswith(old):
                raw = new + raw[len(old):]
                break
        return raw.replace("//", "/")

    db = SessionLocal()
    changed = 0
    try:
        for image in db.query(PostImage).all():
            new_image = clean_path(image.image_url)
            new_video = clean_path(image.video_url)
            if new_image != image.image_url:
                image.image_url = new_image; changed += 1
            if new_video != image.video_url:
                image.video_url = new_video; changed += 1
        for reel in db.query(Reel).all():
            new_video = clean_path(reel.video_url)
            new_thumb = clean_path(reel.thumbnail_url)
            if new_video != reel.video_url:
                reel.video_url = new_video; changed += 1
            if new_thumb != reel.thumbnail_url:
                reel.thumbnail_url = new_thumb; changed += 1
        for story in db.query(Story).all():
            new_media = clean_path(story.media_url)
            if new_media != story.media_url:
                story.media_url = new_media; changed += 1
        for profile in db.query(Profile).all():
            new_picture = clean_path(profile.profile_picture)
            new_cover = clean_path(profile.cover_photo)
            if new_picture != profile.profile_picture:
                profile.profile_picture = new_picture; changed += 1
            if new_cover != profile.cover_photo:
                profile.cover_photo = new_cover; changed += 1
        try:
            for product in db.query(MarketplaceProduct).all():
                new_image = clean_path(product.image_url)
                if new_image != product.image_url:
                    product.image_url = new_image; changed += 1
        except Exception:
            pass
        if changed:
            db.commit()
            logger.info("Normalized %s existing upload path values", changed)
    except Exception as exc:
        db.rollback()
        logger.warning("Could not normalize existing upload paths: %s", exc)
    finally:
        db.close()


def warn_stale_backend_db():
    """Warn when the old backend/socialhub.db exists; runtime uses project-root DB."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    stale_db = os.path.join(project_root, "backend", "socialhub.db")
    root_db = os.path.join(project_root, "socialhub.db")
    if os.path.exists(stale_db):
        logger.warning(
            "Stale backend/socialhub.db detected and ignored. SocialHub uses only %s. "
            "You may archive/delete %s after confirming it has no needed data.",
            root_db,
            stale_db,
        )


def validate_runtime_dependencies():
    """Log clear dependency/setup guidance without exposing secrets.

    This intentionally avoids importing optional integrations such as OpenAI or
    SMTP providers. It verifies the packages required by the configured runtime
    path so setup failures are actionable instead of surfacing as confusing
    stack traces during a request.
    """
    required = {
        "fastapi": "fastapi",
        "sqlalchemy": "sqlalchemy",
        "pydantic": "pydantic",
        "PIL": "Pillow",
        "jose": "python-jose",
        "multipart": "python-multipart",
    }
    if settings.DATABASE_URL_ASYNC.startswith("sqlite+aiosqlite"):
        required["aiosqlite"] = "aiosqlite"
    if settings.DATABASE_URL.startswith("postgresql"):
        required["psycopg2"] = "psycopg2-binary"

    missing = [package for module, package in required.items() if importlib.util.find_spec(module) is None]
    if missing:
        logger.error(
            "Missing Python dependencies: %s. Install with: python -m pip install --upgrade pip && pip install -r requirements.txt",
            ", ".join(sorted(missing)),
        )
    else:
        logger.info("Runtime dependency check passed. Database=%s Uploads=%s", settings.DATABASE_URL.split(":", 1)[0], settings.UPLOAD_DIR)


def run_production_migrations():
    """Run Alembic migrations in production without unsafe fallbacks."""
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=backend_dir, check=True)
    except subprocess.CalledProcessError as e:
        logger.critical(
            "Alembic upgrade failed and startup cannot continue safely: %s. "
            "Database was preserved. Run: cd backend && python -m alembic upgrade head",
            e,
        )
        raise RuntimeError("Production database migration failed; refusing create_all fallback") from e


@app.on_event("startup")
async def startup():
    """Perform safe startup checks without mutating user data unexpectedly."""
    try:
        validate_runtime_dependencies()
        warn_stale_backend_db()
        if settings.DEBUG or settings.AUTO_CREATE_TABLES:
            Base.metadata.create_all(bind=engine)
            if settings.AUTO_SCHEMA_COMPATIBILITY:
                ensure_schema_compatibility()
            logger.info("Database tables created/checked for local development")
        else:
            run_production_migrations()
            logger.info("Database migrations applied successfully")
        if settings.SEED_DEMO_ACCOUNTS:
            logger.warning("SEED_DEMO_ACCOUNTS is deprecated for startup; use backend/scripts/seed_demo.py instead")
    except Exception as e:
        logger.error("Unsafe startup aborted: %s", e)
        raise


# ==================== Error Handlers ====================
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return serve_html(request, "index.html")


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
