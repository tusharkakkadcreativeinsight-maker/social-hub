"""Profile Visit Analytics - Feature 5"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta

from ..database import get_db
from ..models.models import User, ProfileVisit
from ..utils.dependencies import get_current_user
from ..utils.time import utcnow_naive

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/profile-visits")
def get_profile_visits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get profile visit analytics for current user."""
    now = utcnow_naive()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    
    total_visits = db.query(ProfileVisit).filter(
        ProfileVisit.visited_user_id == current_user.id
    ).count()
    
    visits_today = db.query(ProfileVisit).filter(
        ProfileVisit.visited_user_id == current_user.id,
        ProfileVisit.created_at >= today_start
    ).count()
    
    visits_this_week = db.query(ProfileVisit).filter(
        ProfileVisit.visited_user_id == current_user.id,
        ProfileVisit.created_at >= week_start
    ).count()
    
    # Top countries (demo data)
    countries = db.query(
        ProfileVisit.country, func.count(ProfileVisit.id).label('count')
    ).filter(
        ProfileVisit.visited_user_id == current_user.id,
        ProfileVisit.country.isnot(None)
    ).group_by(ProfileVisit.country).order_by(func.count(ProfileVisit.id).desc()).limit(5).all()
    
    # Recent visits
    recent_visits = db.query(ProfileVisit).filter(
        ProfileVisit.visited_user_id == current_user.id
    ).order_by(ProfileVisit.created_at.desc()).limit(20).all()
    
    recent = []
    for v in recent_visits:
        visitor_data = None
        if v.visitor:
            visitor_data = {
                "id": v.visitor.id, "username": v.visitor.username,
                "profile_picture": v.visitor.profile_picture,
            }
        recent.append({
            "id": v.id, "visitor": visitor_data,
            "country": v.country, "created_at": str(v.created_at),
        })
    
    return {
        "total_visits": total_visits,
        "visits_today": visits_today,
        "visits_this_week": visits_this_week,
        "top_countries": [{"country": c[0], "count": c[1]} for c in countries],
        "recent_visits": recent,
    }


@router.post("/track-visit/{username}")
def track_profile_visit(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track a profile visit."""
    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target.id == current_user.id:
        return {"message": "Self-visit not tracked"}
    
    visit = ProfileVisit(
        visited_user_id=target.id,
        visitor_id=current_user.id,
        country="India",  # Demo data
    )
    db.add(visit)
    db.commit()
    return {"message": "Visit tracked"}