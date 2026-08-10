from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta

from ..database import get_db
from ..models.models import Post, Reel, TrendingHashtag
from ..schemas.schemas import PostResponse, PostImageResponse, UserSearchResult, TrendingHashtagResponse
from ..utils.dependencies import get_current_user, get_current_user_optional as get_optional_user
from ..models.models import User

router = APIRouter(prefix="/api/trending", tags=["Trending"])


def build_trending_post_response(post, current_user, db):
    """Build a simplified post response for trending."""
    author_data = None
    if post.author:
        pp = post.author.profile_picture if hasattr(post.author, 'profile_picture') else None
        author_data = UserSearchResult(
            id=post.author.id, username=post.author.username,
            full_name=post.author.full_name, profile_picture=pp,
            is_verified=post.author.is_verified, followers_count=post.author.followers_count,
            badge=getattr(post.author, 'badge', None)
        )

    return PostResponse(
        id=post.id, user_id=post.user_id, content=post.content,
        is_scheduled=post.is_scheduled, scheduled_time=post.scheduled_time,
        is_published=post.is_published, hashtags=post.hashtags,
        post_type=getattr(post, 'post_type', 'normal'),
        repost_id=getattr(post, 'repost_id', None),
        created_at=post.created_at, updated_at=post.updated_at,
        images=[PostImageResponse(
            id=img.id, image_url=img.image_url, is_video=img.is_video,
            video_url=img.video_url, order=img.order
        ) for img in (post.images or [])],
        likes_count=post.likes_count, comments_count=post.comments_count,
        shares_count=getattr(post, 'shares_count', 0),
        author=author_data,
        is_liked=False, is_saved=False
    )


@router.get("/hashtags", response_model=List[TrendingHashtagResponse])
def get_trending_hashtags(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get trending hashtags."""
    # First check if we have cached trending hashtags
    cached = db.query(TrendingHashtag).order_by(TrendingHashtag.count.desc()).limit(limit).all()
    if cached:
        return [TrendingHashtagResponse(hashtag=t.hashtag, count=t.count) for t in cached]

    # Otherwise compute from recent posts (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    posts = db.query(Post).filter(
        Post.is_published == True, Post.is_deleted == False,
        Post.created_at >= week_ago
    ).limit(500).all()

    hashtag_counts = {}
    for post in posts:
        if post.hashtags:
            for tag in post.hashtags:
                tag_lower = tag.lower()
                hashtag_counts[tag_lower] = hashtag_counts.get(tag_lower, 0) + 1

    # Sort by count and save top ones
    sorted_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    for tag, count in sorted_hashtags:
        existing = db.query(TrendingHashtag).filter(TrendingHashtag.hashtag == tag).first()
        if existing:
            existing.count = count
            existing.last_updated = datetime.utcnow()
        else:
            db.add(TrendingHashtag(hashtag=tag, count=count))

    db.commit()

    return [TrendingHashtagResponse(hashtag=f"#{tag}", count=count) for tag, count in sorted_hashtags]


@router.get("/posts", response_model=dict)
def get_trending_posts(
    page: int = 1, page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trending posts based on engagement."""
    week_ago = datetime.utcnow() - timedelta(days=7)
    offset = (page - 1) * page_size

    # Get recent posts with their like counts
    posts = db.query(Post).filter(
        Post.is_published == True, Post.is_deleted == False,
        Post.created_at >= week_ago
    ).all()

    # Score by likes + comments + shares
    scored_posts = []
    for post in posts:
        score = post.likes_count + post.comments_count + getattr(post, 'shares_count', 0)
        scored_posts.append((score, post))

    scored_posts.sort(key=lambda x: x[0], reverse=True)
    total = len(scored_posts)
    paginated = scored_posts[offset:offset + page_size]

    return {
        "posts": [build_trending_post_response(post, current_user, db) for _, post in paginated],
        "total": total, "page": page, "page_size": page_size,
        "has_next": offset + page_size < total
    }


@router.get("/reels", response_model=dict)
def get_trending_reels(
    page: int = 1, page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trending reels based on views and likes."""
    from ..models.models import Reel, ReelLike

    offset = (page - 1) * page_size
    reels = db.query(Reel).filter(Reel.is_deleted == False).all()

    # Score by views + likes
    scored = []
    for reel in reels:
        score = reel.views_count + reel.likes_count
        scored.append((score, reel))

    scored.sort(key=lambda x: x[0], reverse=True)
    total = len(scored)
    paginated = scored[offset:offset + page_size]

    from .reels import build_reel_response
    return {
        "reels": [build_reel_response(reel, current_user, db) for _, reel in paginated],
        "total": total, "page": page, "page_size": page_size,
        "has_next": offset + page_size < total
    }


@router.get("/explore", response_model=dict)
def explore(
    page: int = 1, page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Explore page - mix of trending content."""
    offset = (page - 1) * page_size

    # Get a mix of recent popular posts
    posts = db.query(Post).filter(
        Post.is_published == True, Post.is_deleted == False
    ).order_by(Post.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "posts": [build_trending_post_response(post, current_user, db) for post in posts],
        "page": page, "page_size": page_size,
        "has_next": len(posts) == page_size
    }