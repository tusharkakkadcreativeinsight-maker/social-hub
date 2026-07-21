from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional

from ..config import settings
from ..database import get_db
from ..models.models import Music, User
from ..schemas.schemas import MusicResponse
from ..utils.dependencies import get_current_user, save_upload_file, safe_delete_upload_file, validate_audio_file

router = APIRouter(prefix="/api/music", tags=["Music"])


def _can_manage_music(track: Music, user: User) -> bool:
    return track.user_id == user.id or getattr(track, "created_by", None) == user.id or user.role == "admin"


@router.get("", response_model=list[MusicResponse])
def get_music(category: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(Music)
    if category:
        query = query.filter(Music.category == category)
    limit = max(1, min(limit, 100))
    return query.order_by(Music.is_trending.desc(), Music.created_at.desc()).limit(limit).all()


@router.get("/categories")
def get_music_categories(db: Session = Depends(get_db)):
    rows = db.query(Music.category, func.count(Music.id)).filter(Music.category.isnot(None)).group_by(Music.category).order_by(Music.category.asc()).all()
    return {"categories": [{"name": name, "tracks_count": count} for name, count in rows if name]}


@router.get("/me", response_model=list[MusicResponse])
def get_my_music(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Music).filter(Music.user_id == current_user.id).order_by(Music.created_at.desc()).limit(100).all()


@router.get("/trending", response_model=list[MusicResponse])
def get_trending_music(db: Session = Depends(get_db)):
    return db.query(Music).order_by(Music.is_trending.desc(), Music.use_count.desc(), Music.created_at.desc()).limit(50).all()


@router.get("/search", response_model=list[MusicResponse])
def search_music(q: str = "", db: Session = Depends(get_db)):
    term = f"%{q.strip()}%"
    query = db.query(Music)
    if q.strip():
        query = query.filter(or_(Music.title.ilike(term), Music.artist.ilike(term), Music.category.ilike(term)))
    return query.order_by(Music.is_trending.desc(), Music.created_at.desc()).limit(50).all()


@router.get("/{music_id}", response_model=MusicResponse)
def get_music_track(music_id: str, db: Session = Depends(get_db)):
    track = db.query(Music).filter(Music.id == music_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Music track not found")
    return track


@router.post("/upload", response_model=MusicResponse, status_code=status.HTTP_201_CREATED)
async def upload_music(
    title: str = Form(...),
    artist: str = Form(None),
    duration: float = Form(None),
    category: str = Form(None),
    is_trending: bool = Form(False),
    file: UploadFile = File(None),
    audio_file: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    upload = audio_file or file
    if upload is None:
        raise HTTPException(status_code=400, detail="audio_file is required")
    if not validate_audio_file(upload):
        raise HTTPException(status_code=400, detail="Invalid audio file. Upload MP3, WAV, M4A, or OGG.")
    audio_path = await save_upload_file(settings.UPLOAD_DIR, upload, "music")
    track = Music(
        user_id=current_user.id,
        created_by=current_user.id,
        title=title.strip()[:150],
        artist=(artist or "").strip()[:150] or None,
        audio_path=audio_path,
        duration=duration,
        category=(category or "").strip()[:80] or None,
        is_trending=bool(is_trending),
        use_count=0,
    )
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


@router.patch("/{music_id}", response_model=MusicResponse)
def update_music(
    music_id: str,
    payload: dict = Body(default={}),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    track = db.query(Music).filter(Music.id == music_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Music track not found")
    if not _can_manage_music(track, current_user):
        raise HTTPException(status_code=403, detail="Only the uploader or admin can update this track")

    if "title" in payload:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        track.title = title[:150]
    if "artist" in payload:
        track.artist = str(payload.get("artist") or "").strip()[:150] or None
    if "duration" in payload:
        duration = payload.get("duration")
        track.duration = float(duration) if duration not in (None, "") else None
    if "category" in payload:
        track.category = str(payload.get("category") or "").strip()[:80] or None
    if "is_trending" in payload:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Only admins can change trending status")
        track.is_trending = bool(payload.get("is_trending"))

    db.commit()
    db.refresh(track)
    return track


@router.delete("/{music_id}")
def delete_music(music_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    track = db.query(Music).filter(Music.id == music_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Music track not found")
    if not _can_manage_music(track, current_user):
        raise HTTPException(status_code=403, detail="Only the uploader or admin can delete this track")
    safe_delete_upload_file(track.audio_path)
    db.delete(track)
    db.commit()
    return {"success": True, "message": "Music track deleted"}