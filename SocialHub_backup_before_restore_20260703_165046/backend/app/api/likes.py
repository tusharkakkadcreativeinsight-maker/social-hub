from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.models import User, Post, Like, Notification, ReactionType
from ..schemas.schemas import LikeRequest, LikeResponse, UserSearchResult
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/api/likes", tags=["Likes"])


@router.post("/{post_id}", response_model=LikeResponse)
def like_post(
    post_id: str,
    request: LikeRequest = LikeRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Like or react to a post."""
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check existing like
    existing_like = db.query(Like).filter(
        Like.user_id == current_user.id,
        Like.post_id == post_id
    ).first()

    if existing_like:
        # Update reaction
        existing_like.reaction = request.reaction
        db.commit()
        db.refresh(existing_like)
        return existing_like

    # Create new like
    like = Like(
        user_id=current_user.id,
        post_id=post_id,
        reaction=request.reaction
    )
    db.add(like)
    db.flush()

    # Create notification
    if post.user_id != current_user.id:
        notification = Notification(
            user_id=post.user_id,
            actor_id=current_user.id,
            type="like",
            message=f"{current_user.username} liked your post",
            reference_id=post_id,
            reference_type="post"
        )
        db.add(notification)

    db.commit()
    db.refresh(like)
    return like


@router.delete("/{post_id}")
def unlike_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove like from a post."""
    like = db.query(Like).filter(
        Like.user_id == current_user.id,
        Like.post_id == post_id
    ).first()

    if not like:
        raise HTTPException(status_code=404, detail="Like not found")

    db.delete(like)
    db.commit()
    return {"message": "Like removed successfully"}


@router.get("/{post_id}")
def get_post_likes(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all likes for a post."""
    likes = db.query(Like).filter(Like.post_id == post_id).all()
    result = []
    for like in likes:
        user_data = None
        if like.user:
            user_data = {
                "id": like.user.id,
                "username": like.user.username,
                "full_name": like.user.full_name,
                "profile_picture": like.user.profile_picture if hasattr(like.user, 'profile_picture') else None,
                "is_verified": like.user.is_verified,
                "followers_count": like.user.followers_count
            }
        result.append({
            "id": like.id,
            "user_id": like.user_id,
            "post_id": like.post_id,
            "reaction": like.reaction if like.reaction else "like",
            "created_at": like.created_at.isoformat() if like.created_at else None,
            "user": user_data
        })
    return result
