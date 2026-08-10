from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models.models import User, Reel, ReelLike, ReelSave, ReelComment, Notification, Music
from ..schemas.schemas import ReelCreate, ReelResponse, ReelCommentCreate, UserSearchResult, ReelMusicUpdate
from ..utils.dependencies import get_current_user, save_upload_file, validate_video_file
from ..config import settings
from ..utils.time import utcnow_naive

router = APIRouter(prefix="/api/reels", tags=["Reels"])


def build_reel_response(reel, current_user, db):
    """Build a ReelResponse with computed fields."""
    author_data = None
    if reel.user:
        pp = reel.user.profile_picture if hasattr(reel.user, 'profile_picture') else None
        author_data = UserSearchResult(
            id=reel.user.id, username=reel.user.username, full_name=reel.user.full_name,
            profile_picture=pp, is_verified=reel.user.is_verified,
            followers_count=reel.user.followers_count, badge=getattr(reel.user, 'badge', None)
        )

    is_saved = False
    if current_user:
        is_saved = db.query(ReelSave).filter(
            ReelSave.reel_id == reel.id, ReelSave.user_id == current_user.id
        ).first() is not None

    music_artist = reel.music.artist if getattr(reel, "music", None) else None
    return ReelResponse(
        id=reel.id, user_id=reel.user_id, video_url=reel.video_url,
        thumbnail_url=reel.thumbnail_url, cover_image=getattr(reel, "cover_image", None) or reel.thumbnail_url,
        caption=reel.caption, hashtags=reel.hashtags, location=getattr(reel, "location", None),
        music_id=getattr(reel, "music_id", None), music_name=getattr(reel, "music_name", None), music_artist=music_artist,
        visibility=getattr(reel, "visibility", "public") or "public", views_count=reel.views_count,
        shares_count=getattr(reel, 'shares_count', 0),
        created_at=reel.created_at, likes_count=reel.likes_count,
        comments_count=reel.comments_count, user=author_data,
        is_liked=any(like.user_id == current_user.id for like in (reel.likes or [])) if current_user else False,
        is_saved=is_saved
    )


def build_reel_upload_payload(reel, current_user, db):
    response = build_reel_response(reel, current_user, db)
    data = jsonable_encoder(response)
    data["music_name"] = getattr(reel, "music_name", None)
    data["cover_image"] = getattr(reel, "cover_image", None) or getattr(reel, "thumbnail_url", None)
    return {"success": True, "reel": data, **data}


def _parse_hashtags(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    tags = []
    for part in raw.replace("#", "").replace(" ", ",").split(","):
        tag = part.strip().lower()
        if tag and tag not in tags:
            tags.append(tag[:80])
    return tags or None


@router.post("", response_model=ReelResponse, status_code=status.HTTP_201_CREATED)
async def create_reel(
    caption: str = Form(None),
    hashtags: str = Form(None),
    title: str = Form(None),
    music_name: str = Form(None),
    music_id: str = Form(None),
    audio_name: str = Form(None),
    location: str = Form(None),
    visibility: str = Form("public"),
    text_overlay: str = Form(None),
    filter_name: str = Form(None),
    trim_start: float = Form(None),
    trim_end: float = Form(None),
    is_draft: bool = Form(False),
    file: UploadFile = File(...),
    thumbnail: UploadFile = File(None),
    cover: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new reel."""
    if not validate_video_file(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reel video. Upload MP4, WEBM, or MOV up to 100MB."
        )
    try:
        if trim_start is not None and trim_end is not None and trim_end <= trim_start:
            raise HTTPException(status_code=400, detail="trim_end must be greater than trim_start")
        if visibility not in {"public", "private"}:
            raise HTTPException(status_code=400, detail="visibility must be public or private")
        selected_music = None
        if music_id:
            selected_music = db.query(Music).filter(Music.id == music_id).first()
            if not selected_music:
                raise HTTPException(status_code=404, detail="Selected music not found")
        file_path = await save_upload_file(settings.UPLOAD_DIR, file, "reels")
        thumbnail_path = None
        cover_file = cover or thumbnail
        if cover_file:
            from ..utils.dependencies import validate_image_file
            if not validate_image_file(cover_file):
                raise HTTPException(status_code=400, detail="Invalid reel cover image")
            thumbnail_path = await save_upload_file(settings.UPLOAD_DIR, cover_file, "covers")
        hashtag_list = _parse_hashtags(hashtags)
        reel = Reel(
            user_id=current_user.id,
            video_url=file_path,
            thumbnail_url=thumbnail_path,
            cover_image=thumbnail_path,
            caption=(caption or None),
            hashtags=hashtag_list,
            music_id=selected_music.id if selected_music else None,
            music_name=(music_name or (f"{selected_music.title} - {selected_music.artist}" if selected_music and selected_music.artist else selected_music.title if selected_music else None) or title or None),
            audio_name=(audio_name or None),
            location=(location or None),
            visibility=visibility,
            text_overlay=(text_overlay or None),
            filter_name=(filter_name or None),
            trim_start=trim_start,
            trim_end=trim_end,
            edit_metadata={"is_draft": bool(is_draft)},
        )
        db.add(reel)
        db.commit()
        db.refresh(reel)
        return build_reel_response(reel, current_user, db)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save reel in database") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not upload reel video") from exc


async def upload_reel_compat(
    caption: str = Form(None),
    hashtags: str = Form(None),
    title: str = Form(None),
    music_name: str = Form(None),
    music_id: str = Form(None),
    audio_name: str = Form(None),
    location: str = Form(None),
    visibility: str = Form("public"),
    text_overlay: str = Form(None),
    filter_name: str = Form(None),
    trim_start: float = Form(None),
    trim_end: float = Form(None),
    is_draft: bool = Form(False),
    file: UploadFile = File(...),
    thumbnail: UploadFile = File(None),
    cover: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clean alias implementation registered from aliases.py only."""
    reel_response = await create_reel(caption=caption, hashtags=hashtags, title=title, music_name=music_name, music_id=music_id, audio_name=audio_name, location=location, visibility=visibility, text_overlay=text_overlay, filter_name=filter_name, trim_start=trim_start, trim_end=trim_end, is_draft=is_draft, file=file, thumbnail=thumbnail, cover=cover, current_user=current_user, db=db)
    reel = db.query(Reel).filter(Reel.id == reel_response.id).first()
    return build_reel_upload_payload(reel, current_user, db)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_reel(
    caption: str = Form(None),
    hashtags: str = Form(None),
    title: str = Form(None),
    music_name: str = Form(None),
    music_id: str = Form(None),
    audio_name: str = Form(None),
    location: str = Form(None),
    visibility: str = Form("public"),
    text_overlay: str = Form(None),
    filter_name: str = Form(None),
    trim_start: float = Form(None),
    trim_end: float = Form(None),
    is_draft: bool = Form(False),
    file: UploadFile = File(...),
    thumbnail: UploadFile = File(None),
    cover: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a reel using the explicit frontend endpoint /api/reels/upload."""
    return await upload_reel_compat(caption=caption, hashtags=hashtags, title=title, music_name=music_name, music_id=music_id, audio_name=audio_name, location=location, visibility=visibility, text_overlay=text_overlay, filter_name=filter_name, trim_start=trim_start, trim_end=trim_end, is_draft=is_draft, file=file, thumbnail=thumbnail, cover=cover, current_user=current_user, db=db)


@router.get("", response_model=dict)
def get_reels(
    page: int = 1, page_size: int = 10,
    music_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get reels feed."""
    offset = (page - 1) * page_size
    query = db.query(Reel).filter(Reel.is_deleted == False, Reel.visibility == "public")
    if music_id:
        query = query.filter(Reel.music_id == music_id)
    total = query.count()

    reels = query.order_by(Reel.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "reels": [build_reel_response(r, current_user, db) for r in reels],
        "total": total, "page": page, "page_size": page_size,
        "has_next": offset + page_size < total
    }


@router.get("/saved", response_model=dict)
def get_saved_reels(
    page: int = 1, page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get saved reels. Must stay above /{reel_id} to avoid 404 shadowing."""
    offset = (page - 1) * page_size
    saves = db.query(ReelSave).filter(ReelSave.user_id == current_user.id
    ).order_by(ReelSave.created_at.desc()).offset(offset).limit(page_size).all()

    reels = []
    for save in saves:
        reel = db.query(Reel).filter(Reel.id == save.reel_id, Reel.is_deleted == False).first()
        if reel:
            reels.append(build_reel_response(reel, current_user, db))

    total = db.query(ReelSave).filter(ReelSave.user_id == current_user.id).count()
    return {"reels": reels, "total": total, "page": page, "page_size": page_size, "has_next": offset + page_size < total}


@router.get("/viewer", response_model=dict)
def get_reels_viewer(
    page: int = 1, page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Full reels viewer feed optimized for vertical playback."""
    return get_reels(page=page, page_size=page_size, current_user=current_user, db=db)


@router.get("/user/{user_id}", response_model=dict)
def get_user_reels(
    user_id: str,
    page: int = 1,
    page_size: int = 12,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get reels uploaded by a specific user for profile tabs."""
    offset = (page - 1) * page_size
    total = db.query(Reel).filter(
        Reel.user_id == user_id,
        Reel.is_deleted == False,
    ).count()
    reels = db.query(Reel).filter(
        Reel.user_id == user_id,
        Reel.is_deleted == False,
    ).order_by(Reel.created_at.desc()).offset(offset).limit(page_size).all()
    return {
        "reels": [build_reel_response(reel, current_user, db) for reel in reels],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total,
    }


@router.get("/{reel_id}", response_model=ReelResponse)
def get_reel(
    reel_id: str, current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single reel."""
    reel = db.query(Reel).filter(Reel.id == reel_id, Reel.is_deleted == False).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")

    reel.views_count += 1
    db.commit()
    return build_reel_response(reel, current_user, db)


@router.post("/{reel_id}/like")
def like_reel(reel_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Like a reel."""
    reel = db.query(Reel).filter(Reel.id == reel_id, Reel.is_deleted == False).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")

    existing = db.query(ReelLike).filter(ReelLike.reel_id == reel_id, ReelLike.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already liked this reel")

    db.add(ReelLike(reel_id=reel_id, user_id=current_user.id))
    if reel.user_id != current_user.id:
        db.add(Notification(
            user_id=reel.user_id,
            actor_id=current_user.id,
            type="like",
            message=f"{current_user.username} liked your reel",
            reference_id=reel_id,
            reference_type="reel"
        ))
    db.commit()
    return {"message": "Reel liked"}


@router.delete("/{reel_id}/like")
def unlike_reel(reel_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Unlike a reel."""
    like = db.query(ReelLike).filter(ReelLike.reel_id == reel_id, ReelLike.user_id == current_user.id).first()
    if not like:
        raise HTTPException(status_code=404, detail="Like not found")
    db.delete(like)
    db.commit()
    return {"message": "Reel unliked"}


@router.post("/{reel_id}/save")
def toggle_save_reel(reel_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Save/unsave a reel."""
    reel = db.query(Reel).filter(Reel.id == reel_id, Reel.is_deleted == False).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")

    existing = db.query(ReelSave).filter(ReelSave.reel_id == reel_id, ReelSave.user_id == current_user.id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "Reel unsaved", "saved": False}

    db.add(ReelSave(reel_id=reel_id, user_id=current_user.id))
    db.commit()
    return {"message": "Reel saved", "saved": True}


@router.post("/{reel_id}/share")
def share_reel(reel_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Track a reel share and notify the owner."""
    reel = db.query(Reel).filter(Reel.id == reel_id, Reel.is_deleted == False).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    reel.shares_count = (getattr(reel, "shares_count", 0) or 0) + 1
    if reel.user_id != current_user.id:
        db.add(Notification(
            user_id=reel.user_id,
            actor_id=current_user.id,
            type="share",
            message=f"{current_user.username} shared your reel",
            reference_id=reel_id,
            reference_type="reel"
        ))
    db.commit()
    return {"message": "Reel shared", "shares_count": reel.shares_count}


@router.post("/{reel_id}/music", response_model=ReelResponse)
def update_reel_music(
    reel_id: str, request: ReelMusicUpdate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    reel = db.query(Reel).filter(Reel.id == reel_id, Reel.is_deleted == False).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    if reel.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the reel owner can update music")
    music = db.query(Music).filter(Music.id == request.music_id).first()
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")
    reel.music_id = music.id
    reel.music_name = f"{music.title} - {music.artist}" if music.artist else music.title
    music.use_count = (music.use_count or 0) + 1
    db.commit()
    db.refresh(reel)
    return build_reel_response(reel, current_user, db)


@router.post("/{reel_id}/comments")
def comment_on_reel(
    reel_id: str, request: ReelCommentCreate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Comment on a reel."""
    reel = db.query(Reel).filter(Reel.id == reel_id, Reel.is_deleted == False).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")

    comment = ReelComment(reel_id=reel_id, user_id=current_user.id, content=request.content)
    db.add(comment)
    if reel.user_id != current_user.id:
        db.add(Notification(
            user_id=reel.user_id,
            actor_id=current_user.id,
            type="comment",
            message=f"{current_user.username} commented on your reel",
            reference_id=reel_id,
            reference_type="reel"
        ))
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/{reel_id}/comments")
def get_reel_comments(reel_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get comments for a reel."""
    comments = db.query(ReelComment).filter(
        ReelComment.reel_id == reel_id, ReelComment.is_deleted == False
    ).order_by(ReelComment.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "reel_id": c.reel_id,
            "user_id": c.user_id,
            "content": c.content,
            "likes_count": c.likes_count,
            "created_at": c.created_at,
            "author": {
                "id": c.user.id,
                "username": c.user.username,
                "full_name": c.user.full_name,
                "profile_picture": c.user.profile_picture,
                "is_verified": c.user.is_verified,
                "followers_count": c.user.followers_count,
                "badge": getattr(c.user, "badge", None),
            } if c.user else None,
        }
        for c in comments
    ]


@router.delete("/{reel_id}")
def delete_reel(reel_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a reel."""
    reel = db.query(Reel).filter(Reel.id == reel_id).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    if reel.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can delete only your own reel")
    reel.is_deleted = True
    reel.deleted_at = utcnow_naive()
    db.commit()
    return {"message": "Reel deleted successfully"}