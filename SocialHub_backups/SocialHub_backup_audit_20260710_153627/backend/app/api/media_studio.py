import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models.models import (
    User, OriginalMediaAsset, MediaImportLog, Post, PostImage, Reel, Notification
)
from ..utils.dependencies import get_current_user, save_upload_file
from ..config import settings
from ..utils.time import utcnow_naive

router = APIRouter(prefix="/api/media", tags=["Media Studio"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}
ALLOWED_MEDIA_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def validate_media_file(file: UploadFile) -> bool:
    """Validate media file type and size."""
    if file.content_type and file.content_type not in ALLOWED_MEDIA_TYPES:
        # Check by extension fallback
        ext = (file.filename or "").lower().split(".")[-1] if "." in (file.filename or "") else ""
        if ext not in {"jpg", "jpeg", "png", "gif", "webp", "mp4", "webm", "mov", "avi"}:
            return False
    return True


def get_media_type(file: UploadFile) -> str:
    """Determine if file is image or video."""
    if file.content_type and file.content_type.startswith("video"):
        return "video"
    ext = (file.filename or "").lower().split(".")[-1] if "." in (file.filename or "") else ""
    if ext in {"mp4", "webm", "mov", "avi"}:
        return "video"
    return "image"


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a media asset to the media library."""
    if not validate_media_file(file):
        raise HTTPException(
            status_code=400,
            detail="Invalid media type. Allowed: JPEG, PNG, GIF, WebP, MP4, WebM, MOV, AVI"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Seek back to start
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max 100MB")
    
    try:
        file_path = await save_upload_file(settings.UPLOAD_DIR, file, "original_media")
        media_type = get_media_type(file)
        
        asset = OriginalMediaAsset(
            user_id=current_user.id,
            filename=os.path.basename(file_path),
            original_filename=file.filename or "untitled",
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            media_type=media_type,
            ownership_confirmed=True,
        )
        db.add(asset)
        
        # Log the upload
        log = MediaImportLog(
            user_id=current_user.id,
            asset_id=asset.id,
            action="upload",
            source="upload",
            status="success",
        )
        db.add(log)
        db.commit()
        db.refresh(asset)
        
        return {
            "message": "Media uploaded successfully",
            "asset": {
                "id": asset.id,
                "filename": asset.filename,
                "original_filename": asset.original_filename,
                "file_url": f"/uploads/{asset.file_path}",
                "file_size": asset.file_size,
                "media_type": asset.media_type,
                "mime_type": asset.mime_type,
                "created_at": asset.created_at,
            }
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(exc)}")


@router.get("/library")
def get_media_library(
    page: int = 1,
    page_size: int = 20,
    media_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's media library."""
    offset = (page - 1) * page_size
    query = db.query(OriginalMediaAsset).filter(
        OriginalMediaAsset.user_id == current_user.id
    )
    
    if media_type and media_type in ("image", "video"):
        query = query.filter(OriginalMediaAsset.media_type == media_type)
    
    total = query.count()
    assets = query.order_by(
        OriginalMediaAsset.created_at.desc()
    ).offset(offset).limit(page_size).all()
    
    return {
        "assets": [
            {
                "id": a.id,
                "filename": a.filename,
                "original_filename": a.original_filename,
                "file_url": f"/uploads/{a.file_path}",
                "file_size": a.file_size,
                "media_type": a.media_type,
                "mime_type": a.mime_type,
                "is_used_in_post": a.is_used_in_post,
                "is_used_in_reel": a.is_used_in_reel,
                "created_at": a.created_at,
            }
            for a in assets
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total,
    }


@router.post("/{media_id}/create-post", status_code=status.HTTP_201_CREATED)
def create_post_from_media(
    media_id: str,
    content: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a post from a media asset."""
    asset = db.query(OriginalMediaAsset).filter(
        OriginalMediaAsset.id == media_id,
        OriginalMediaAsset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
    
    post = Post(
        user_id=current_user.id,
        content=content or None,
        is_published=True,
        post_type="normal",
    )
    db.add(post)
    db.flush()
    
    post_image = PostImage(
        post_id=post.id,
        image_url=asset.file_path,
        is_video=(asset.media_type == "video"),
        video_url=asset.file_path if asset.media_type == "video" else None,
        order=0,
    )
    db.add(post_image)
    
    asset.is_used_in_post = True
    
    # Log
    log = MediaImportLog(
        user_id=current_user.id,
        asset_id=asset.id,
        action="create_post",
        source="upload",
        status="success",
    )
    db.add(log)
    db.commit()
    db.refresh(post)
    
    return {"message": "Post created from media", "post_id": post.id}


@router.post("/{media_id}/create-reel", status_code=status.HTTP_201_CREATED)
def create_reel_from_media(
    media_id: str,
    caption: str = Form(""),
    hashtags: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a reel from a media asset."""
    asset = db.query(OriginalMediaAsset).filter(
        OriginalMediaAsset.id == media_id,
        OriginalMediaAsset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
    
    if asset.media_type != "video":
        raise HTTPException(status_code=400, detail="Only video assets can be used for reels")
    
    # Parse hashtags
    hashtag_list = None
    if hashtags:
        tags = []
        for part in hashtags.replace("#", "").replace(" ", ",").split(","):
            tag = part.strip().lower()
            if tag and tag not in tags:
                tags.append(tag[:80])
        hashtag_list = tags or None
    
    reel = Reel(
        user_id=current_user.id,
        video_url=asset.file_path,
        caption=caption or None,
        hashtags=hashtag_list,
    )
    db.add(reel)
    
    asset.is_used_in_reel = True
    
    # Log
    log = MediaImportLog(
        user_id=current_user.id,
        asset_id=asset.id,
        action="create_reel",
        source="upload",
        status="success",
    )
    db.add(log)
    db.commit()
    db.refresh(reel)
    
    return {"message": "Reel created from media", "reel_id": reel.id}


@router.delete("/{media_id}")
def delete_media(
    media_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a media asset."""
    asset = db.query(OriginalMediaAsset).filter(
        OriginalMediaAsset.id == media_id,
        OriginalMediaAsset.user_id == current_user.id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
    
    # Don't delete if used in post or reel
    if asset.is_used_in_post or asset.is_used_in_reel:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete media that is used in a post or reel. Remove the post/reel first."
        )
    
    db.delete(asset)
    db.commit()
    
    return {"message": "Media asset deleted"}