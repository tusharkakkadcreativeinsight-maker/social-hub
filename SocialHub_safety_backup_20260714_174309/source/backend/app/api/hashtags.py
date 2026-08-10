"""Hashtag Pages - Feature 8"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional

from ..database import get_db
from ..models.models import Post, Reel, Hashtag, HashtagTrend, TrendingHashtag, User, Like, Comment
from ..utils.dependencies import get_current_user_optional
from ..schemas.schemas import PostResponse, PostImageResponse, ReelResponse, UserSearchResult

router = APIRouter(prefix="/api/hashtags", tags=["Hashtags"])


@router.get("/search")
def search_hashtags(
    q: str = Query("", min_length=1),
    db: Session = Depends(get_db)
):
    """Search hashtags with count."""
    search = q.lower().replace("#", "")
    
    trends = db.query(HashtagTrend).filter(
        HashtagTrend.hashtag.ilike(f"%{search}%")
    ).order_by(HashtagTrend.trend_score.desc()).limit(20).all()
    
    # Also search from posts/reels
    all_posts = db.query(Post).filter(
        Post.is_published == True, Post.is_deleted == False
    ).limit(500).all()
    
    hashtag_counts = {}
    for post in all_posts:
        if post.hashtags:
            for tag in post.hashtags:
                if search in tag.lower():
                    hashtag_counts[tag] = hashtag_counts.get(tag, 0) + 1
    
    for reel in db.query(Reel).filter(Reel.is_deleted == False).limit(500).all():
        for tag in reel.hashtags or []:
            if search in tag.lower():
                hashtag_counts[tag] = hashtag_counts.get(tag, 0) + 1
    
    trend_map = {t.hashtag: t.trend_score for t in trends}
    
    result = []
    seen = set()
    for tag, count in sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:20]:
        if tag not in seen:
            result.append({
                "hashtag": f"#{tag}", "count": count,
                "trend_score": trend_map.get(tag, 0.0),
            })
            seen.add(tag)
    # Add trend-only results
    for t in trends:
        if t.hashtag not in seen:
            result.append({
                "hashtag": f"#{t.hashtag}",
                "count": t.post_count,
                "trend_score": t.trend_score,
            })
            seen.add(t.hashtag)
    
    return {"hashtags": result, "total": len(result)}


@router.get("/trending")
def get_trending_hashtags(
    db: Session = Depends(get_db)
):
    """Get trending hashtags."""
    trends = db.query(HashtagTrend).order_by(
        HashtagTrend.trend_score.desc()
    ).limit(30).all()
    
    if not trends:
        # Fallback to trending_hashtags table
        trending = db.query(TrendingHashtag).order_by(
            TrendingHashtag.count.desc()
        ).limit(30).all()
        return {
            "trending": [
                {"hashtag": f"#{t.hashtag}", "count": t.count, "trend_score": 0.0}
                for t in trending
            ]
        }
    
    return {
        "trending": [
            {
                "hashtag": f"#{t.hashtag}",
                "count": t.post_count,
                "trend_score": t.trend_score,
                "total_likes": t.total_likes,
                "total_comments": t.total_comments,
            }
            for t in trends
        ]
    }


@router.get("/{hashtag}")
def get_hashtag_page(
    hashtag: str,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """Get posts and reels for a hashtag."""
    tag = hashtag.lower().replace("#", "")
    
    # Get hashtag info
    trend = db.query(HashtagTrend).filter(HashtagTrend.hashtag == tag).first()
    post_count = trend.post_count if trend else 0
    
    # Search posts with hashtag
    offset = (page - 1) * page_size
    all_posts = db.query(Post).filter(
        Post.is_published == True, Post.is_deleted == False
    ).limit(500).all()
    
    matched_posts = []
    for post in all_posts:
        if post.hashtags and any(tag == h.lower() for h in post.hashtags):
            matched_posts.append(post)
        if len(matched_posts) >= page_size:
            break
    
    # Search reels with hashtag
    matched_reels = []
    all_reels = db.query(Reel).filter(Reel.is_deleted == False).limit(200).all()
    for reel in all_reels:
        if reel.hashtags and any(tag == h.lower() for h in reel.hashtags):
            matched_reels.append(reel)
        if len(matched_reels) >= 10:
            break
    
    return {
        "hashtag": f"#{tag}",
        "post_count": post_count or len(matched_posts),
        "trend_score": trend.trend_score if trend else 0.0,
        "posts": [
            {
                "id": p.id, "content": p.content,
                "images": [{"image_url": img.image_url} for img in p.images[:1]] if p.images else [],
                "likes_count": p.likes_count,
                "comments_count": p.comments_count,
                "created_at": str(p.created_at),
                "author": {
                    "id": p.author.id, "username": p.author.username,
                    "profile_picture": p.author.profile_picture,
                    "is_verified": p.author.is_verified,
                } if p.author else None,
            }
            for p in matched_posts
        ],
        "reels": [
            {
                "id": r.id, "caption": r.caption,
                "thumbnail_url": r.thumbnail_url,
                "video_url": r.video_url,
                "views_count": r.views_count,
                "likes_count": r.likes_count,
                "created_at": str(r.created_at),
                "user": {
                    "id": r.user.id, "username": r.user.username,
                    "profile_picture": r.user.profile_picture,
                    "is_verified": r.user.is_verified,
                } if r.user else None,
            }
            for r in matched_reels
        ],
    }