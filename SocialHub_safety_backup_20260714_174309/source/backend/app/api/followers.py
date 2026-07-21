from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.models import User, Follower, Notification, AccountType
from ..utils.email import send_push_notification
from ..schemas.schemas import FollowResponse, FollowListResponse, UserSearchResult
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/api/follow", tags=["Followers"])


@router.post("/{user_id}", response_model=FollowResponse)
def follow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Follow a user."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already following
    existing = db.query(Follower).filter(
        Follower.follower_id == current_user.id,
        Follower.following_id == user_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already following this user")

    # Check if private account (requires follow request)
    is_pending = target_user.account_type == AccountType.PRIVATE

    # Block check placeholder - integrate Block model when available
    # if user_is_blocked(current_user.id, user_id):
    #     raise HTTPException(status_code=403, detail="Cannot follow this user")

    follow = Follower(
        follower_id=current_user.id,
        following_id=user_id,
        is_pending=is_pending
    )
    db.add(follow)
    db.flush()

    # Create notification
    notification_type = "follow_request" if is_pending else "follow"
    message = f"{current_user.username} sent a follow request" if is_pending else f"{current_user.username} started following you"

    notification = Notification(
        user_id=target_user.id,
        actor_id=current_user.id,
        type=notification_type,
        message=message,
        reference_id=current_user.id,
        reference_type="user"
    )
    db.add(notification)

    db.commit()
    db.refresh(follow)
    return follow


@router.delete("/{user_id}")
def unfollow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unfollow a user."""
    follow = db.query(Follower).filter(
        Follower.follower_id == current_user.id,
        Follower.following_id == user_id
    ).first()

    if not follow:
        raise HTTPException(status_code=404, detail="Not following this user")

    db.delete(follow)
    db.commit()
    return {"message": "Unfollowed successfully"}


@router.get("/followers/{user_id}", response_model=dict)
def get_followers(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get followers of a user."""
    offset = (page - 1) * page_size
    follows = db.query(Follower).filter(
        Follower.following_id == user_id,
        Follower.is_pending == False
    ).offset(offset).limit(page_size).all()

    users = []
    for f in follows:
        user = db.query(User).filter(User.id == f.follower_id).first()
        if user:
            users.append(UserSearchResult(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                profile_picture=user.profile_picture if hasattr(user, 'profile_picture') else None,
                is_verified=user.is_verified,
                followers_count=user.followers_count
            ))

    total = db.query(Follower).filter(
        Follower.following_id == user_id,
        Follower.is_pending == False
    ).count()

    return {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total
    }


@router.get("/following/{user_id}", response_model=dict)
def get_following(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get users that a user is following."""
    offset = (page - 1) * page_size
    follows = db.query(Follower).filter(
        Follower.follower_id == user_id,
        Follower.is_pending == False
    ).offset(offset).limit(page_size).all()

    users = []
    for f in follows:
        user = db.query(User).filter(User.id == f.following_id).first()
        if user:
            users.append(UserSearchResult(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                profile_picture=user.profile_picture if hasattr(user, 'profile_picture') else None,
                is_verified=user.is_verified,
                followers_count=user.followers_count
            ))

    total = db.query(Follower).filter(
        Follower.follower_id == user_id,
        Follower.is_pending == False
    ).count()

    return {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total
    }


@router.get("/requests", response_model=List[UserSearchResult])
def get_follow_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pending follow requests for current user."""
    follows = db.query(Follower).filter(
        Follower.following_id == current_user.id,
        Follower.is_pending == True
    ).all()

    users = []
    for f in follows:
        user = db.query(User).filter(User.id == f.follower_id).first()
        if user:
            users.append(UserSearchResult(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                profile_picture=user.profile_picture if hasattr(user, 'profile_picture') else None,
                is_verified=user.is_verified,
                followers_count=user.followers_count
            ))

    return users


@router.post("/accept/{user_id}")
def accept_follow_request(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept a follow request."""
    follow = db.query(Follower).filter(
        Follower.follower_id == user_id,
        Follower.following_id == current_user.id,
        Follower.is_pending == True
    ).first()

    if not follow:
        raise HTTPException(status_code=404, detail="Follow request not found")

    follow.is_pending = False
    db.commit()

    # Create notification
    notification = Notification(
        user_id=user_id,
        actor_id=current_user.id,
        type="accept_follow",
        message=f"{current_user.username} accepted your follow request",
        reference_id=current_user.id,
        reference_type="user"
    )
    db.add(notification)
    db.commit()

    return {"message": "Follow request accepted"}


@router.delete("/reject/{user_id}")
def reject_follow_request(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject a follow request."""
    follow = db.query(Follower).filter(
        Follower.follower_id == user_id,
        Follower.following_id == current_user.id,
        Follower.is_pending == True
    ).first()

    if not follow:
        raise HTTPException(status_code=404, detail="Follow request not found")

    db.delete(follow)
    db.commit()
    return {"message": "Follow request rejected"}


@router.get("/check/{user_id}")
def check_follow_status(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if current user is following another user."""
    follow = db.query(Follower).filter(
        Follower.follower_id == current_user.id,
        Follower.following_id == user_id
    ).first()

    return {
        "is_following": follow is not None,
        "is_pending": follow.is_pending if follow else False
    }