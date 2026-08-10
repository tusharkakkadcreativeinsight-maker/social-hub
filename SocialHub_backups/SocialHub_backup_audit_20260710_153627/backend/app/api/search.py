"""Search System Pro - Feature 7"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from ..database import get_db
from ..models.models import User, Post, Reel, ReelSave, RecentSearch, HashtagTrend
from ..schemas.schemas import SearchResponse, UserSearchResult, PostResponse, PostImageResponse, ReelResponse
from ..utils.dependencies import get_current_user, get_current_user_optional
from ..utils.time import utcnow_naive

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query("", max_length=100),
    type: Optional[str] = Query(None, pattern="^(users|posts|reels|hashtags|all)$"),
    page: int = 1,
    page_size: int = 10,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Global search for users, posts, and hashtags."""
    search_term = (q or "").strip().lower()
    result = SearchResponse()
    
    # Save to recent searches if user is logged in and has search term
    if current_user and search_term:
        existing = db.query(RecentSearch).filter(
            RecentSearch.user_id == current_user.id,
            RecentSearch.query == search_term
        ).first()
        if not existing:
            # Keep only last 20 searches
            count = db.query(RecentSearch).filter(RecentSearch.user_id == current_user.id).count()
            if count >= 20:
                oldest = db.query(RecentSearch).filter(
                    RecentSearch.user_id == current_user.id
                ).order_by(RecentSearch.created_at.asc()).first()
                if oldest:
                    db.delete(oldest)
            
            rs = RecentSearch(
                user_id=current_user.id,
                search_type="text",
                query=search_term,
            )
            db.add(rs)
            db.commit()

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
                followers_count=user.followers_count,
                badge=getattr(user, 'badge', None),
            )
            for user in users
        ]
        # Save user search
        if current_user and users and search_term:
            for u in users:
                existing_usr = db.query(RecentSearch).filter(
                    RecentSearch.user_id == current_user.id,
                    RecentSearch.target_user_id == u.id,
                    RecentSearch.search_type == 'user'
                ).first()
                if not existing_usr:
                    rs = RecentSearch(
                        user_id=current_user.id,
                        search_type="user",
                        query=u.username,
                        target_user_id=u.id,
                    )
                    db.add(rs)
            db.commit()

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
                author=UserSearchResult(
                    id=post.author.id, username=post.author.username,
                    full_name=post.author.full_name,
                    profile_picture=post.author.profile_picture if hasattr(post.author, 'profile_picture') else None,
                    is_verified=post.author.is_verified,
                ) if post.author else None,
            )
            for post in posts
        ]

    # Search reels by caption or hashtag
    if type in [None, "all", "reels"]:
        reel_query = db.query(Reel).filter(Reel.is_deleted == False)
        reels = reel_query.order_by(Reel.created_at.desc()).limit(300).all()
        matched_reels = []
        for reel in reels:
            caption_match = search_term and search_term in (reel.caption or "").lower()
            hashtag_match = search_term and any(search_term.replace("#", "") in str(tag).lower() for tag in (reel.hashtags or []))
            if not search_term or caption_match or hashtag_match:
                matched_reels.append(reel)
            if len(matched_reels) >= page_size:
                break
        result.reels = [
            ReelResponse(
                id=reel.id,
                user_id=reel.user_id,
                video_url=reel.video_url,
                thumbnail_url=reel.thumbnail_url,
                caption=reel.caption,
                hashtags=reel.hashtags,
                views_count=reel.views_count,
                shares_count=getattr(reel, "shares_count", 0),
                created_at=reel.created_at,
                likes_count=reel.likes_count,
                comments_count=reel.comments_count,
                user=UserSearchResult(
                    id=reel.user.id,
                    username=reel.user.username,
                    full_name=reel.user.full_name,
                    profile_picture=reel.user.profile_picture if hasattr(reel.user, 'profile_picture') else None,
                    is_verified=reel.user.is_verified,
                    followers_count=reel.user.followers_count,
                    badge=getattr(reel.user, 'badge', None),
                ) if reel.user else None,
                is_liked=any(like.user_id == current_user.id for like in (reel.likes or [])) if current_user else False,
                is_saved=db.query(ReelSave).filter(ReelSave.reel_id == reel.id, ReelSave.user_id == current_user.id).first() is not None if current_user else False,
            )
            for reel in matched_reels
        ]

    # Search hashtags - iterate all published posts looking for matching hashtags
    if type in [None, "all", "hashtags"]:
        all_posts = db.query(Post).filter(
            Post.is_published == True,
            Post.is_deleted == False
        ).limit(500).all()

        hashtags_set = {}
        for post in all_posts:
            if post.hashtags:
                for tag in post.hashtags:
                    if not search_term or search_term in tag.lower():
                        hashtags_set[tag] = hashtags_set.get(tag, 0) + 1
        for reel in db.query(Reel).filter(Reel.is_deleted == False).limit(500).all():
            for tag in reel.hashtags or []:
                if not search_term or search_term.replace("#", "") in str(tag).lower():
                    hashtags_set[tag] = hashtags_set.get(tag, 0) + 1
        
        # Get trend scores
        trend_scores = {}
        trends = db.query(HashtagTrend).filter(HashtagTrend.hashtag.in_([k for k in hashtags_set.keys()])).all()
        for t in trends:
            trend_scores[t.hashtag] = t.trend_score
        
        result.hashtags = [
            f"#{tag}" 
            for tag, count in sorted(hashtags_set.items(), key=lambda x: (trend_scores.get(x[0], 0), x[1]), reverse=True)[:10]
        ]

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
            followers_count=user.followers_count,
            badge=getattr(user, 'badge', None),
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


@router.get("/suggestions")
def get_search_suggestions(
    q: str = Query("", max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get search suggestions based on query."""
    search_term = (q or "").strip().lower()
    
    users = []
    hashtags = []
    
    if search_term:
        # User suggestions
        user_results = db.query(User).filter(
            or_(
                User.username.ilike(f"%{search_term}%"),
                User.full_name.ilike(f"%{search_term}%")
            ),
            User.is_banned == False,
            User.is_active == True,
            User.id != current_user.id
        ).limit(5).all()
        
        users = [
            {
                "type": "user",
                "id": u.id, "username": u.username,
                "full_name": u.full_name,
                "profile_picture": u.profile_picture,
                "is_verified": u.is_verified,
            }
            for u in user_results
        ]
        
        # Hashtag suggestions
        tag_results = db.query(HashtagTrend).filter(
            HashtagTrend.hashtag.ilike(f"%{search_term}%")
        ).order_by(HashtagTrend.trend_score.desc()).limit(5).all()
        
        hashtags = [
            {"type": "hashtag", "hashtag": f"#{t.hashtag}", "count": t.post_count, "trend_score": t.trend_score}
            for t in tag_results
        ]
    
    return {"suggestions": users + hashtags}


@router.get("/recent")
def get_recent_searches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent searches for current user."""
    searches = db.query(RecentSearch).filter(
        RecentSearch.user_id == current_user.id
    ).order_by(RecentSearch.created_at.desc()).limit(20).all()
    
    result = []
    for s in searches:
        item = {
            "id": s.id,
            "query": s.query,
            "search_type": s.search_type,
            "created_at": str(s.created_at),
        }
        if s.target_user:
            item["target_user"] = {
                "id": s.target_user.id,
                "username": s.target_user.username,
                "profile_picture": s.target_user.profile_picture,
            }
        result.append(item)
    
    return {"searches": result}


@router.delete("/recent")
def clear_recent_searches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all recent searches."""
    db.query(RecentSearch).filter(RecentSearch.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Search history cleared"}


@router.delete("/recent/{search_id}")
def delete_recent_search(
    search_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a single recent search."""
    search = db.query(RecentSearch).filter(
        RecentSearch.id == search_id,
        RecentSearch.user_id == current_user.id
    ).first()
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")
    db.delete(search)
    db.commit()
    return {"message": "Search entry removed"}