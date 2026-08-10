from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.models import User, Notification, NotificationSetting
from ..schemas.schemas import (
    NotificationResponse, NotificationSettingResponse, NotificationSettingUpdate, UserSearchResult
)
from ..utils.dependencies import get_current_user
from ..utils.email import send_push_notification

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    page: int = 1, page_size: int = 20, type: Optional[str] = None, unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notifications for current user."""
    offset = (page - 1) * page_size
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if type and type != "all":
        query = query.filter(Notification.type == type)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(page_size).all()

    result = []
    for n in notifications:
        actor_data = None
        if n.actor:
            pp = n.actor.profile_picture if hasattr(n.actor, 'profile_picture') else None
            actor_data = UserSearchResult(
                id=n.actor.id, username=n.actor.username, full_name=n.actor.full_name,
                profile_picture=pp, is_verified=n.actor.is_verified,
                followers_count=n.actor.followers_count, badge=getattr(n.actor, 'badge', None)
            )
        result.append(NotificationResponse(
            id=n.id, user_id=n.user_id, actor_id=n.actor_id,
            type=n.type, message=n.message, reference_id=n.reference_id,
            reference_type=n.reference_type, is_read=n.is_read,
            created_at=n.created_at, actor=actor_data
        ))
    return result


@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get unread notifications count."""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == False
    ).count()
    return {"unread_count": count}


@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == current_user.id
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}


@router.put("/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Mark all notifications as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}


@router.get("/settings", response_model=NotificationSettingResponse)
def get_notification_settings(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get notification settings."""
    settings = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id
    ).first()

    if not settings:
        settings = NotificationSetting(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


@router.put("/settings", response_model=NotificationSettingResponse)
def update_notification_settings(
    request: NotificationSettingUpdate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Update notification settings."""
    settings = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id
    ).first()

    if not settings:
        settings = NotificationSetting(user_id=current_user.id)
        db.add(settings)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return settings


@router.post("/push-send")
def send_push_notification_endpoint(
    device_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
    current_user: User = Depends(get_current_user)
):
    """Send a push notification to a device (user's own device)."""
    from ..utils.email import send_push_notification
    sent = send_push_notification(device_token, title, body, data)
    if not sent:
        raise HTTPException(status_code=501, detail="Push notifications not configured")
    return {"message": "Push notification sent"}
