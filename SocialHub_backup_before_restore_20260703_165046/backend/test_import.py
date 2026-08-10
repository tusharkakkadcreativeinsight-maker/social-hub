import sys
import traceback
sys.path.insert(0, '.')

try:
    print("Testing imports...")
    from app.config import settings
    print(f"✓ Config loaded: {settings.APP_NAME}")
    
    from app.database import engine, Base, get_db
    print("✓ Database module loaded")
    
    from app.models.models import User, Post, Profile
    print("✓ Models loaded")
    
    from app.schemas.schemas import RegisterRequest, Token
    print("✓ Schemas loaded")
    
    from app.utils.security import hash_password, verify_password, create_access_token
    print("✓ Security module loaded")
    
    from app.utils.dependencies import get_current_user
    print("✓ Dependencies loaded")
    
    from app.utils.email import send_verification_email
    print("✓ Email module loaded")
    
    from app.api import (
        auth_router, users_router, posts_router, likes_router,
        comments_router, followers_router, stories_router, reels_router,
        messaging_router, notifications_router, search_router,
        reports_router, admin_router
    )
    print("✓ All API routers loaded")
    
    from app.websocket.chat import handle_chat_websocket
    print("✓ WebSocket module loaded")
    
    from main import app
    print("✓ FastAPI app created")
    
    print("\n✅ All imports successful!")
    
except Exception as e:
    print(f"\n❌ Import error: {e}")
    traceback.print_exc()
    sys.exit(1)