from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from ..database import get_db
from ..models.models import User, Post
from ..schemas.schemas import SearchResponse, UserSearchResult, PostResponse, PostImageResponse
from ..utils.dependencies import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query("", max_length=100),
    type: Optional[str] = Query(None, pattern="^(users|posts|hashtags|all)$"),
    page: int = 1,
    page_size: int = 10,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Global search for users, posts, and hashtags."""
    search_term = (q or "").strip().lower()
    result = SearchResponse()

    # Search users
    if type in [None, "all", "users"]:
        user_query = db.query(User).filter(User.is_banned == False, User.is_active == True)
        if search_term:
            user_query = user_query.filter(or_(
                User.username.ilike(f"%{search_term}%"),
                User.full_name.ilike(f"%{search_term}%"),
                User.email.ilike(f"%{search_term}%")
            ))
        users = user_query.order_by(User.created_at.desc()).limit(page_size).all()

        result.users = [
            UserSearchResult(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                profile_picture=user.profile_picture if hasattr(user, 'profile_picture') else None,
                is_verified=user.is_verified,
                followers_count=user.followers_count
            )
            for user in users
        ]

    # Search posts
    if type in [None, "all", "posts"]:
        post_query = db.query(Post).filter(Post.is_published == True, Post.is_deleted == False)
        if search_term:
            post_query = post_query.filter(Post.content.ilike(f"%{search_term}%"))
        posts = post_query.order_by(Post.created_at.desc()).limit(page_size).all()

        result.posts = [
            PostResponse(
                id=post.id,
                user_id=post.user_id,
                content=post.content,
                is_scheduled=post.is_scheduled,
                scheduled_time=post.scheduled_time,
                is_published=post.is_published,
                hashtags=post.hashtags,
                created_at=post.created_at,
                updated_at=post.updated_at,
                images=[PostImageResponse(
                    id=img.id,
                    image_url=img.image_url,
                    is_video=img.is_video,
                    video_url=img.video_url,
                    order=img.order
                ) for img in (post.images or [])],
                likes_count=post.likes_count,
                comments_count=post.comments_count,
                is_liked=any(like.user_id == current_user.id for like in (post.likes or [])) if current_user else False,
                author=post.author
            )
            for post in posts
        ]

    # Search hashtags - iterate all published posts looking for matching hashtags
    if type in [None, "all", "hashtags"]:
        all_posts = db.query(Post).filter(
            Post.is_published == True,
            Post.is_deleted == False
        ).limit(500).all()

        hashtags_set = set()
        for post in all_posts:
            if post.hashtags:
                for tag in post.hashtags:
                    if not search_term or search_term in tag.lower():
                        hashtags_set.add(f"#{tag}")
        result.hashtags = list(hashtags_set)[:10]

    return result


@router.get("/users", response_model=List[UserSearchResult])
def search_users(
    q: str = Query(..., min_length=1),
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users by username or full name."""
    offset = (page - 1) * page_size
    users = db.query(User).filter(
        or_(
            User.username.ilike(f"%{q}%"),
            User.full_name.ilike(f"%{q}%")
        ),
        User.is_banned == False,
        User.is_active == True
    ).offset(offset).limit(page_size).all()

    return [
        UserSearchResult(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            profile_picture=user.profile_picture if hasattr(user, 'profile_picture') else None,
            is_verified=user.is_verified,
            followers_count=user.followers_count
        )
        for user in users
    ]


@router.get("/hashtags")
def search_hashtags(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search hashtags and return related post count."""
    all_posts = db.query(Post).filter(
        Post.is_published == True,
        Post.is_deleted == False
    ).limit(500).all()

    search_term = q.lower()
    hashtag_counts = {}
    for post in all_posts:
        if post.hashtags:
            for tag in post.hashtags:
                if search_term in tag.lower():
                    hashtag_counts[tag] = hashtag_counts.get(tag, 0) + 1

    return [
        {"hashtag": f"#{tag}", "count": count}
        for tag, count in sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    ]