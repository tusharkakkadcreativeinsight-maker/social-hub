import os
import sys
from fastapi import FastAPI, WebSocket, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
import logging
import subprocess

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
    , aliases_router
)
from app.api.data_studio import router as data_studio_router
from app.api.advanced import router as advanced_router

from app.websocket.chat import handle_chat_websocket


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
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

# Paths
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
static_dir = os.path.join(frontend_dir, "static")
uploads_dir = os.path.join(frontend_dir, "uploads")
templates_dir = os.path.join(frontend_dir, "templates")

# Create directories if they don't exist
os.makedirs(static_dir, exist_ok=True)
os.makedirs(uploads_dir, exist_ok=True)
for upload_subdir in ("posts", "reels", "stories", "profiles", "covers"):
    os.makedirs(os.path.join(uploads_dir, upload_subdir), exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


def serve_html(filename: str):
    """Serve an HTML template file."""
    filepath = os.path.join(templates_dir, filename)
    if not os.path.exists(filepath):
        filepath = os.path.join(templates_dir, "index.html")
    return FileResponse(filepath, media_type="text/html")


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
app.include_router(data_studio_router, prefix="/api/data-studio")
app.include_router(advanced_router)

# ==================== Health Check ====================


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION
    }


# ==================== WebSocket Endpoint ====================
@app.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket endpoint for real-time chat."""
    await handle_chat_websocket(websocket, token)


# ==================== Frontend Routes ====================
@app.get("/")
async def serve_index():
    return serve_html("index.html")


@app.get("/login")
async def serve_login():
    return serve_html("login.html")


@app.get("/register")
async def serve_register():
    return serve_html("register.html")


@app.get("/profile/{username}")
async def serve_profile(username: str):
    return serve_html("profile.html")


@app.get("/posts")
async def serve_posts():
    return serve_html("posts.html")


@app.get("/chat")
async def serve_chat():
    return serve_html("chat.html")


@app.get("/chat/{chat_id}")
async def serve_chat_room(chat_id: str):
    return serve_html("chat.html")


@app.get("/stories")
async def serve_stories():
    return serve_html("stories.html")


@app.get("/reels")
async def serve_reels():
    return serve_html("reels.html")


@app.get("/notifications")
async def serve_notifications():
    return serve_html("notifications.html")


@app.get("/search")
async def serve_search():
    return serve_html("search.html")


@app.get("/admin")
async def serve_admin():
    return serve_html("admin.html")


@app.get("/forgot-password")
async def serve_forgot_password():
    return serve_html("forgot_password.html")


@app.get("/reset-password")
async def serve_reset_password(token: str = ""):
    return serve_html("reset_password.html")


@app.get("/explore")
async def serve_explore():
    return serve_html("search.html")


@app.get("/bookmarks")
async def serve_bookmarks():
    return serve_html("posts.html")


@app.get("/edit-profile")
async def serve_edit_profile():
    return serve_html("profile.html")


@app.get("/settings")
async def serve_settings():
    return serve_html("settings.html")


@app.get("/instagram-studio")
async def serve_instagram_studio():
    return serve_html("instagram_studio.html")


@app.get("/connect-instagram")
async def serve_connect_instagram():
    return serve_html("connect_instagram.html")


@app.get("/data-studio")
async def serve_data_studio():
    return serve_html("data_studio.html")


@app.get("/creator-dashboard")
async def serve_creator_dashboard():
    return serve_html("creator_dashboard.html")


@app.get("/scheduled")
async def serve_scheduled_posts():
    return serve_html("scheduled.html")


@app.get("/marketplace")
async def serve_marketplace():
    return serve_html("marketplace.html")


@app.get("/collabs")
async def serve_collabs():
    return serve_html("collabs.html")


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
        "reels": {
            "edit_metadata": "TEXT",
            "trim_start": "FLOAT",
            "trim_end": "FLOAT",
            "text_overlay": "VARCHAR(255)",
            "filter_name": "VARCHAR(100)",
            "music_name": "VARCHAR(150)",
        },
        "scheduled_posts": {
            "content_type": "VARCHAR(20) DEFAULT 'post' NOT NULL",
            "platform": "VARCHAR(20) DEFAULT 'socialhub' NOT NULL",
            "published_at": "DATETIME",
        },
        "stories": {
            "is_archived": "BOOLEAN DEFAULT 0 NOT NULL",
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


def run_production_migrations():
    """Run Alembic migrations in production instead of create_all()."""
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=backend_dir, check=True)


@app.on_event("startup")
async def startup():
    """Initialize database tables on startup."""
    try:
        warn_stale_backend_db()
        if settings.DEBUG or settings.AUTO_CREATE_TABLES:
            Base.metadata.create_all(bind=engine)
            ensure_schema_compatibility()
            logger.info("Database tables created/checked for local development")
        else:
            run_production_migrations()
            logger.info("Database migrations applied successfully")
        ensure_demo_accounts()
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")


# ==================== Error Handlers ====================
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return serve_html("index.html")


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)