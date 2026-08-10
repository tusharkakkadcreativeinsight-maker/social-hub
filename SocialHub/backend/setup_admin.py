"""Script to set up admin user and seed data."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.models import User, UserRole, Profile, NotificationSetting
from app.utils.security import hash_password

db = SessionLocal()
try:
    def ensure_admin(email: str, username: str, password: str, full_name: str):
        """Create or normalize an admin account used by local smoke tests."""
        admin = db.query(User).filter(User.email == email).first()
        if not admin:
            admin = db.query(User).filter(User.username == username).first()

        if not admin:
            admin = User(
                email=email,
                username=username,
                full_name=full_name,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN.value,
                is_active=True,
                is_banned=False,
                is_verified=True,
                is_email_verified=True,
                account_type="public"
            )
            db.add(admin)
            db.flush()
            print(f"✓ Admin user created: {username} / {password}")
        else:
            admin.email = email
            admin.username = username
            admin.full_name = admin.full_name or full_name
            admin.hashed_password = hash_password(password)
            admin.role = UserRole.ADMIN.value
            admin.is_active = True
            admin.is_banned = False
            admin.is_verified = True
            admin.is_email_verified = True
            print(f"✓ Admin user exists: {username} / {password}")

        if not db.query(Profile).filter(Profile.user_id == admin.id).first():
            db.add(Profile(user_id=admin.id, bio="SocialHub Administrator"))
        if not db.query(NotificationSetting).filter(NotificationSetting.user_id == admin.id).first():
            db.add(NotificationSetting(user_id=admin.id))

    # Support both the documented local admin and the comprehensive API test admin.
    ensure_admin("admin@socialhub.com", "admin", "Admin123!", "Admin User")
    ensure_admin("admin@example.com", "adminuser", "AdminPass123", "Admin User")
    db.commit()

    print("\nUsers in database:")
    users = db.query(User).all()
    for u in users:
        print(f"  {u.username} ({u.email}) - role: {u.role}")
finally:
    db.close()