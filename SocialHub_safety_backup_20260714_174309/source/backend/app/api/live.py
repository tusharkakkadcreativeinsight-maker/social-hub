from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.models import User, LiveStream, LiveViewer, AuditLog
from ..utils.dependencies import get_current_user
from ..utils.time import utcnow_naive
from ..websocket.live import live_manager

router = APIRouter(prefix="/api/live", tags=["Live"])


class LiveStartRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    camera_enabled: bool = False
    microphone_enabled: bool = True


def _is_admin(user: User) -> bool:
    return user.role == "admin"


def _live_payload(live: LiveStream):
    return {
        "id": live.id,
        "host_id": live.host_id,
        "title": live.title,
        "description": live.description,
        "status": live.status,
        "camera_enabled": live.camera_enabled,
        "microphone_enabled": live.microphone_enabled,
        "viewer_count": live.viewer_count,
        "likes_count": live.likes_count,
        "gifts_count": live.gifts_count,
        "started_at": live.started_at,
        "ended_at": live.ended_at,
        "host": {
            "id": live.host.id,
            "username": live.host.username,
            "full_name": live.host.full_name,
            "profile_picture": live.host.profile_picture,
            "is_verified": live.host.is_verified,
        } if live.host else None,
    }


@router.post("/start", status_code=status.HTTP_201_CREATED)
def start_live(request: LiveStartRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    active = db.query(LiveStream).filter(LiveStream.host_id == current_user.id, LiveStream.status == "active", LiveStream.is_deleted == False).first()
    if active:
        return {"message": "Existing active live returned", "live": _live_payload(active)}
    live = LiveStream(host_id=current_user.id, title=request.title.strip(), description=request.description, camera_enabled=request.camera_enabled, microphone_enabled=request.microphone_enabled)
    db.add(live)
    db.commit()
    db.refresh(live)
    return {"message": "Live started", "live": _live_payload(live)}


@router.post("/end/{live_id}")
async def end_live(live_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    live = db.query(LiveStream).filter(LiveStream.id == live_id, LiveStream.is_deleted == False).first()
    if not live:
        raise HTTPException(status_code=404, detail="Live stream not found")
    if live.host_id != current_user.id and not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only the host or admin can end this live")
    live.status = "ended"
    live.ended_at = utcnow_naive()
    live.viewer_count = 0
    db.query(LiveViewer).filter(LiveViewer.live_id == live_id, LiveViewer.is_active == True).update({"is_active": False, "left_at": utcnow_naive()})
    db.commit()
    await live_manager.broadcast(live_id, {"type": "live_ended", "live_id": live_id})
    return {"message": "Live ended", "live": _live_payload(live)}


@router.get("/active")
def active_lives(db: Session = Depends(get_db)):
    lives = db.query(LiveStream).filter(LiveStream.status == "active", LiveStream.is_deleted == False).order_by(LiveStream.created_at.desc()).all()
    return {"lives": [_live_payload(live) for live in lives]}


@router.get("/my-history")
def my_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lives = db.query(LiveStream).filter(LiveStream.host_id == current_user.id, LiveStream.is_deleted == False).order_by(LiveStream.created_at.desc()).all()
    return {"lives": [_live_payload(live) for live in lives]}


@router.get("/{live_id}")
def get_live(live_id: str, db: Session = Depends(get_db)):
    live = db.query(LiveStream).filter(LiveStream.id == live_id, LiveStream.is_deleted == False).first()
    if not live:
        raise HTTPException(status_code=404, detail="Live stream not found")
    return _live_payload(live)


@router.post("/{live_id}/join")
async def join_live(live_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    live = db.query(LiveStream).filter(LiveStream.id == live_id, LiveStream.status == "active", LiveStream.is_deleted == False).first()
    if not live:
        raise HTTPException(status_code=404, detail="Active live stream not found")
    viewer = db.query(LiveViewer).filter(LiveViewer.live_id == live_id, LiveViewer.user_id == current_user.id).first()
    if viewer:
        viewer.is_active = True; viewer.left_at = None
    else:
        db.add(LiveViewer(live_id=live_id, user_id=current_user.id))
    db.flush()
    live.viewer_count = db.query(LiveViewer).filter(LiveViewer.live_id == live_id, LiveViewer.is_active == True).count()
    db.commit()
    await live_manager.broadcast(live_id, {"type": "viewer_count", "viewer_count": live.viewer_count})
    return {"message": "Joined live", "viewer_count": live.viewer_count}


@router.post("/{live_id}/leave")
async def leave_live(live_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    viewer = db.query(LiveViewer).filter(LiveViewer.live_id == live_id, LiveViewer.user_id == current_user.id, LiveViewer.is_active == True).first()
    if viewer:
        viewer.is_active = False; viewer.left_at = utcnow_naive()
    live = db.query(LiveStream).filter(LiveStream.id == live_id).first()
    if not live:
        raise HTTPException(status_code=404, detail="Live stream not found")
    live.viewer_count = db.query(LiveViewer).filter(LiveViewer.live_id == live_id, LiveViewer.is_active == True).count()
    db.commit()
    await live_manager.broadcast(live_id, {"type": "viewer_count", "viewer_count": live.viewer_count})
    return {"message": "Left live", "viewer_count": live.viewer_count}


@router.post("/{live_id}/like")
async def like_live(live_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    live = db.query(LiveStream).filter(LiveStream.id == live_id, LiveStream.status == "active", LiveStream.is_deleted == False).first()
    if not live:
        raise HTTPException(status_code=404, detail="Active live stream not found")
    live.likes_count += 1
    db.commit()
    await live_manager.broadcast(live_id, {"type": "live_like", "live_id": live_id, "likes_count": live.likes_count, "user_id": current_user.id})
    return {"message": "Liked", "likes_count": live.likes_count}


@router.post("/{live_id}/gift")
async def gift_live(live_id: str, gift: dict = Body(default={}), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    live = db.query(LiveStream).filter(LiveStream.id == live_id, LiveStream.status == "active", LiveStream.is_deleted == False).first()
    if not live:
        raise HTTPException(status_code=404, detail="Active live stream not found")
    live.gifts_count += 1
    db.commit()
    await live_manager.broadcast(live_id, {"type": "live_gift", "live_id": live_id, "gifts_count": live.gifts_count, "gift": gift, "user_id": current_user.id})
    return {"message": "Gift sent", "gifts_count": live.gifts_count}


@router.delete("/{live_id}")
def delete_live(live_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    live = db.query(LiveStream).filter(LiveStream.id == live_id).first()
    if not live:
        raise HTTPException(status_code=404, detail="Live stream not found")
    if live.host_id != current_user.id and not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only the host or admin can delete this live")
    live.is_deleted = True
    live.status = "deleted"
    live.deleted_at = utcnow_naive()
    if _is_admin(current_user) and current_user.id != live.host_id:
        db.add(AuditLog(admin_id=current_user.id, action="delete", target_type="live", target_id=live_id, reason="Admin deleted live stream"))
    db.commit()
    return {"message": "Live stream deleted"}
