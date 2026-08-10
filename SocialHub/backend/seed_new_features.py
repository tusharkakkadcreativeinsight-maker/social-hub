"""Seed demo data for new features and run migrations."""
import sys
import os
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app.models.models import (
    User, Profile, VerificationRequest, SavedCollection, CollectionItem,
    ProfileVisit, CreatorWallet, EarningRecord, PayoutRequest, RecentSearch,
    HashtagTrend, UserOnlineStatus, DeletedMessage, StoryHighlight
)
from app.utils.security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_demo_data():
    """Seed demo data for new features."""
    db = SessionLocal()
    try:
        # Get or create demo user
        demo_user = db.query(User).filter(User.email == "test@test.com").first()
        if not demo_user:
            logger.warning("Demo user not found. Please ensure test@test.com exists.")
            return
        
        # Create wallet if not exists
        wallet = db.query(CreatorWallet).filter(CreatorWallet.user_id == demo_user.id).first()
        if not wallet:
            wallet = CreatorWallet(user_id=demo_user.id, balance=0.0, total_earned=0.0, total_withdrawn=0.0)
            db.add(wallet)
            db.flush()
        
        # Seed demo earnings
        if db.query(EarningRecord).filter(EarningRecord.user_id == demo_user.id).count() == 0:
            demo_earnings = [
                EarningRecord(user_id=demo_user.id, amount=250.00, source="reel", description="Reel earnings - Summer Vibes"),
                EarningRecord(user_id=demo_user.id, amount=180.00, source="post", description="Sponsored post - Tech Review"),
                EarningRecord(user_id=demo_user.id, amount=500.00, source="collab", description="Brand collaboration - Fashion Week"),
                EarningRecord(user_id=demo_user.id, amount=75.00, source="bonus", description="Creator bonus - July 2026"),
                EarningRecord(user_id=demo_user.id, amount=320.00, source="reel", description="Reel earnings - Travel Diary"),
            ]
            for earning in demo_earnings:
                db.add(earning)
                wallet.balance += earning.amount
                wallet.total_earned += earning.amount
            logger.info(f"Added {len(demo_earnings)} demo earnings")
        
        # Seed demo collections
        if db.query(SavedCollection).filter(SavedCollection.user_id == demo_user.id).count() == 0:
            col1 = SavedCollection(user_id=demo_user.id, name="Favorites")
            col2 = SavedCollection(user_id=demo_user.id, name="Watch Later")
            db.add(col1)
            db.add(col2)
            db.flush()
            logger.info("Created demo collections")
        
        # Seed demo online status
        online_status = db.query(UserOnlineStatus).filter(UserOnlineStatus.user_id == demo_user.id).first()
        if not online_status:
            online_status = UserOnlineStatus(user_id=demo_user.id, is_online=True)
            db.add(online_status)
            logger.info("Created online status")
        
        # Seed demo profile visits
        if db.query(ProfileVisit).filter(ProfileVisit.visited_user_id == demo_user.id).count() == 0:
            for i in range(15):
                visit = ProfileVisit(
                    visited_user_id=demo_user.id,
                    visitor_id=demo_user.id,  # Self-visits for demo
                    ip_address="192.168.1.100",
                    country="India",
                    created_at=datetime.utcnow() - timedelta(days=i)
                )
                db.add(visit)
            logger.info("Created 15 demo profile visits")
        
        db.commit()
        logger.info("Demo data seeded successfully")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding demo data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()