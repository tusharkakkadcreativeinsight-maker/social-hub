from fastapi import APIRouter, Depends, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.models import User
from ..utils.dependencies import get_current_user
from .posts import get_premium_feed, upload_post_compat
from .reels import get_reels, upload_reel_compat, like_reel
from .users import get_user_profile, upload_profile_picture
from .followers import follow_user, unfollow_user

router = APIRouter(prefix="/api", tags=["Compatibility API"])


@router.get("/feed")
def feed_alias(page: int = 1, page_size: int = 10, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_premium_feed(page=page, page_size=page_size, current_user=current_user, db=db)


@router.get("/reels")
def reels_alias(page: int = 1, page_size: int = 10, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_reels(page=page, page_size=page_size, current_user=current_user, db=db)


@router.get("/profile/{username}")
def profile_alias(username: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_user_profile(username=username, current_user=current_user, db=db)


@router.post("/profile/photo")
async def profile_photo_alias(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await upload_profile_picture(file=file, current_user=current_user, db=db)


@router.post("/posts/upload")
async def posts_upload_alias(
    caption: str = Form(None),
    content: str = Form(None),
    hashtags: str = Form(None),
    files: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await upload_post_compat(content=content, caption=caption, hashtags=hashtags, files=files, current_user=current_user, db=db)


@router.post("/reels/upload")
async def reels_upload_alias(caption: str = Form(None), hashtags: str = Form(None), file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await upload_reel_compat(caption=caption, hashtags=hashtags, file=file, current_user=current_user, db=db)


@router.post("/reels/{reel_id}/like")
def reel_like_alias(reel_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return like_reel(reel_id=reel_id, current_user=current_user, db=db)


@router.post("/follow/{user_id}")
def follow_alias(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return follow_user(user_id=user_id, current_user=current_user, db=db)


@router.post("/unfollow/{user_id}")
def unfollow_alias(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return unfollow_user(user_id=user_id, current_user=current_user, db=db)