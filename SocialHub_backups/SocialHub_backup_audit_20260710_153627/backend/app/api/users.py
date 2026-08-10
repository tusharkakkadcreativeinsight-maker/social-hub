from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import os

from ..database import get_db
from ..models.models import User, Profile, Follower, SocialLink, Post, Story, Reel
from ..schemas.schemas import (
    UserProfileResponse, UpdateProfileRequest, UserSearchResult,
    UserResponse, SocialLinkCreate, SocialLinkResponse
)
from ..utils.dependencies import get_current_user, save_upload_file, validate_image_file, get_current_user_optional, safe_delete_upload_file
from ..config import settings

router = APIRouter(prefix="/api/users", tags=["Users"])


def build_profile_response(user, db):
    """Build full profile response."""
    pp = user.profile_picture if hasattr(user, 'profile_picture') else None
    cp = user.cover_photo if hasattr(user, 'cover_photo') else None

    social_links = []
    for link in user.social_links:
        social_links.append(SocialLinkResponse(id=link.id, platform=link.platform, url=link.url))

    reels_count = len(user.reels) if hasattr(user, 'reels') and user.reels else 0

    return UserProfileResponse(
        id=user.id, username=user.username, full_name=user.full_name,
        email=user.email,
        bio=user.profile.bio if user.profile else None,
        profile_picture=pp, cover_photo=cp,
        website=user.profile.website if user.profile else None,
        location=user.profile.location if user.profile else None,
        phone_number=user.profile.phone_number if user.profile else None,
        date_of_birth=user.profile.date_of_birth if user.profile else None,
        gender=user.profile.gender if user.profile else None,
        account_type=user.account_type, is_verified=user.is_verified,
        followers_count=user.followers_count, following_count=user.following_count,
        posts_count=user.posts_count, reels_count=reels_count, created_at=user.created_at,
        badge=getattr(user, 'badge', None), social_links=social_links
    )


def ensure_profile(user: User, db: Session) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


@router.get("/me/profile", response_model=UserProfileResponse)
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get logged-in user's editable profile."""
    ensure_profile(current_user, db)
    return build_profile_response(current_user, db)


@router.put("/me/profile", response_model=UserProfileResponse)
def update_my_profile(request: UpdateProfileRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Instagram-like profile update alias for the current user."""
    return update_profile(request=request, current_user=current_user, db=db)


@router.post("/me/profile-image")
async def upload_profile_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Upload/change current user's profile image using clean relative paths."""
    return await upload_profile_picture(file=file, current_user=current_user, db=db)


@router.delete("/me/profile-image")
def delete_profile_image(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove current user's profile image."""
    return remove_profile_picture(current_user=current_user, db=db)


@router.get("/profile/{username}", response_model=UserProfileResponse)
def get_user_profile(
    username: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get user profile by username."""
    user = db.query(User).filter(User.username == username.lower()).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return build_profile_response(user, db)


@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile."""
    profile = ensure_profile(current_user, db)

    update_data = request.model_dump(exclude_unset=True, exclude_none=True)

    if "full_name" in update_data:
        current_user.full_name = update_data.pop("full_name")

    if "account_type" in update_data:
        current_user.account_type = update_data["account_type"]

    for field, value in update_data.items():
        if hasattr(profile, field):
            setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    db.refresh(current_user)
    return build_profile_response(current_user, db)


@router.put("/profile/social-links", response_model=List[SocialLinkResponse])
def replace_social_links(
    links: List[SocialLinkCreate],
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Replace current user's visible social links from the profile/settings UI."""
    db.query(SocialLink).filter(SocialLink.user_id == current_user.id).delete()
    for link in links[:8]:
        if link.platform and link.url:
            db.add(SocialLink(user_id=current_user.id, platform=link.platform.strip()[:50], url=link.url.strip()[:500]))
    db.commit()
    return db.query(SocialLink).filter(SocialLink.user_id == current_user.id).all()


def delete_old_file(file_path: str):
    """Delete old uploaded file if it exists."""
    safe_delete_upload_file(file_path)


@router.post("/profile/picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Upload profile picture - deletes old one."""
    if not validate_image_file(file):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")

    profile = ensure_profile(current_user, db)

    # Delete old picture
    if profile.profile_picture and not str(profile.profile_picture).startswith("default"):
        delete_old_file(profile.profile_picture)

    file_path = await save_upload_file(settings.UPLOAD_DIR, file, "profiles")
    profile.profile_picture = file_path
    db.commit()
    return {"success": True, "profile_picture": file_path}


@router.get("/profile/picture/me")
def get_my_profile_picture(current_user: User = Depends(get_current_user)):
    return {"profile_picture": current_user.profile_picture}


@router.delete("/profile/picture")
def remove_profile_picture(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = ensure_profile(current_user, db)
    if profile.profile_picture and not str(profile.profile_picture).startswith("default"):
        delete_old_file(profile.profile_picture)
    profile.profile_picture = None
    db.commit()
    return {"success": True, "profile_picture": None}


@router.post("/profile/cover")
async def upload_cover_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Upload cover photo - deletes old one."""
    if not validate_image_file(file):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)
        db.flush()

    # Delete old cover
    if profile.cover_photo:
        delete_old_file(profile.cover_photo)

    file_path = await save_upload_file(settings.UPLOAD_DIR, file, "covers")
    profile.cover_photo = file_path
    db.commit()
    return {"cover_photo": file_path}


# ==================== SOCIAL LINKS ====================
@router.get("/social-links/me", response_model=List[SocialLinkResponse])
def get_my_social_links(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get social links for current user."""
    links = db.query(SocialLink).filter(SocialLink.user_id == current_user.id).all()
    return links


@router.post("/social-links", response_model=SocialLinkResponse, status_code=status.HTTP_201_CREATED)
def add_social_link(
    request: SocialLinkCreate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Add a social link."""
    link = SocialLink(user_id=current_user.id, platform=request.platform, url=request.url)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.delete("/social-links/{link_id}")
def remove_social_link(
    link_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Remove a social link."""
    link = db.query(SocialLink).filter(SocialLink.id == link_id, SocialLink.user_id == current_user.id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    db.delete(link)
    db.commit()
    return {"message": "Social link removed"}


@router.get("/social-links/{user_id}", response_model=List[SocialLinkResponse])
def get_user_social_links(user_id: str, db: Session = Depends(get_db)):
    """Get social links for a user."""
    links = db.query(SocialLink).filter(SocialLink.user_id == user_id).all()
    return links


# ==================== PROFILE ANALYTICS ====================
@router.get("/by-username/{username}", response_model=UserProfileResponse)
def get_user_by_username_api(
    username: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get user by username (API endpoint)."""
    user = db.query(User).filter(User.username == username.lower()).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return build_profile_response(user, db)


@router.get("/analytics/me")
def get_my_analytics(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get profile analytics for current user."""
    total_likes = sum(len(p.likes) for p in current_user.posts)
    total_comments = sum(len(p.comments) for p in current_user.posts)
    total_views = sum(r.views_count for r in current_user.reels)

    return {
        "followers_count": current_user.followers_count,
        "following_count": current_user.following_count,
        "posts_count": current_user.posts_count,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_reel_views": total_views,
        "reels_count": len(current_user.reels) if current_user.reels else 0,
        "stories_count": len([s for s in current_user.stories if not s.is_expired]) if current_user.stories else 0,
    }


# ==================== FOLLOW SUGGESTIONS ====================
@router.get("/suggestions", response_model=List[UserSearchResult])
def get_follow_suggestions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get follow suggestions based on mutual connections."""
    following_ids = [f.following_id for f in current_user.following_rel]
    following_ids.append(current_user.id)

    suggestions = db.query(User).filter(
        User.id.notin_(following_ids),
        User.is_banned == False,
        User.is_active == True
    ).order_by(User.created_at.desc()).limit(10).all()

    return [UserSearchResult(
        id=u.id, username=u.username, full_name=u.full_name,
        profile_picture=u.profile_picture if hasattr(u, 'profile_picture') else None,
        is_verified=u.is_verified, followers_count=u.followers_count,
        badge=getattr(u, 'badge', None)
    ) for u in suggestions]


# ==================== MUTUAL FOLLOWERS ====================
@router.get("/mutual/{user_id}", response_model=List[UserSearchResult])
def get_mutual_followers(
    user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get mutual followers between current user and another user."""
    my_following = set(f.following_id for f in current_user.following_rel)

    other_user = db.query(User).filter(User.id == user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")

    other_following = set(f.following_id for f in other_user.following_rel)
    mutual_ids = my_following.intersection(other_following)

    users = db.query(User).filter(User.id.in_(mutual_ids)).limit(20).all()
    return [UserSearchResult(
        id=u.id, username=u.username, full_name=u.full_name,
        profile_picture=u.profile_picture if hasattr(u, 'profile_picture') else None,
        is_verified=u.is_verified, followers_count=u.followers_count,
        badge=getattr(u, 'badge', None)
    ) for u in users]


@router.get("/{user_id}", response_model=UserProfileResponse)
def get_user_by_id(
    user_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get user by ID. Keep after static /mutual route to avoid shadowing."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return build_profile_response(user, db)