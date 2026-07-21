from app.database import SessionLocal
from app.models.models import User

db = SessionLocal()
users = db.query(User).all()
print(f"Users in DB: {len(users)}")
for u in users:
    print(f"  id={u.id}, username={u.username}, email={u.email}, active={u.is_active}, banned={u.is_banned}")
db.close()