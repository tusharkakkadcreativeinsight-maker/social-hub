from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models.models import User, Reel, ReelLike, ReelSave, ReelComment
from ..schemas.schemas import ReelCreate, ReelResponse, ReelCommentCreate, UserSearchResult
from ..utils.dependencies import get_current_user, save_upload_file, validate_video_file
from ..config import settings

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

    return ReelResponse(
        id=reel.id, user_id=reel.user_id, video_url=reel.video_url,
        thumbnail_url=reel.thumbnail_url, caption=reel.caption,
        hashtags=reel.hashtags, views_count=reel.views_count,
        shares_count=getattr(reel, 'shares_count', 0),
        created_at=reel.created_at, likes_count=reel.likes_count,
        comments_count=reel.comments_count, user=author_data,
        is_liked=any(like.user_id == current_user.id for like in (reel.likes or [])) if current_user else False,
        is_saved=is_saved
    )


@router.post("", response_model=ReelResponse, status_code=status.HTTP_201_CREATED)
async def create_reel(
    caption: str = Form(None),
    hashtags: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new reel."""
    if not validate_video_file(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video file. Only MP4, MOV, AVI, and WEBM are allowed"
        )

    file_path = await save_upload_file(settings.UPLOAD_DIR, file, "reels")
    hashtag_list = [t.strip().lower() for t in hashtags.split(",")] if hashtags else None

    reel = Reel(user_id=current_user.id, video_url=file_path, caption=caption, hashtags=hashtag_list)
    db.add(reel)
    db.commit()
    db.refresh(reel)
    return build_reel_response(reel, current_user, db)


async def upload_reel_compat(
    caption: str = Form(None),
    hashtags: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clean alias implementation registered from aliases.py only."""
    return await create_reel(caption=caption, hashtags=hashtags, file=file, current_user=current_user, db=db)


@router.get("", response_model=dict)
def get_reels(
    page: int = 1, page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get reels feed."""
    offset = (page - 1) * page_size
    total = db.query(Reel).filter(Reel.is_deleted == False).count()

    reels = db.query(Reel).filter(Reel.is_deleted == False
    ).order_by(Reel.created_at.desc()).offset(offset).limit(page_size).all()

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
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/{reel_id}/comments")
def get_reel_comments(reel_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get comments for a reel."""
    comments = db.query(ReelComment).filter(
        ReelComment.reel_id == reel_id, ReelComment.is_deleted == False
    ).order_by(ReelComment.created_at.desc()).all()
    return comments


@router.delete("/{reel_id}")
def delete_reel(reel_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a reel."""
    reel = db.query(Reel).filter(Reel.id == reel_id, Reel.user_id == current_user.id).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found or not authorized")
    reel.is_deleted = True
    db.commit()
    return {"message": "Reel deleted successfully"}