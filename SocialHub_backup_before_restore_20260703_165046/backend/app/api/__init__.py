"""API routes package - exports all routers."""
from .auth import router as auth_router
from .users import router as users_router
from .posts import router as posts_router
from .likes import router as likes_router
from .comments import router as comments_router
from .followers import router as followers_router
from .stories import router as stories_router
from .reels import router as reels_router
from .messaging import router as messaging_router
from .notifications import router as notifications_router
from .search import router as search_router
from .reports import router as reports_router
from .admin import router as admin_router
from .trending import router as trending_router
from .instagram import router as instagram_router
from .ai_chat import router as ai_chat_router
from .aliases import router as aliases_router

__all__ = [
    "auth_router", "users_router", "posts_router", "likes_router",
    "comments_router", "followers_router", "stories_router", "reels_router",
    "messaging_router", "notifications_router", "search_router",
    "reports_router", "admin_router", "trending_router", "instagram_router", "ai_chat_router", "aliases_router",
]



