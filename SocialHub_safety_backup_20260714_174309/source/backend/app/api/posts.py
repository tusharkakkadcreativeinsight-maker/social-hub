from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import json
from datetime import timedelta

from ..database import get_db
from ..models.models import (
    User, Post, PostImage, Like, Comment, CommentReaction, Follower, Notification,
    post_tags, Bookmark, PostShare, Poll, PollOption, PollVote
)
from ..schemas.schemas import (
    PostCreate, PostUpdate, PostResponse, PostFeedResponse, PostImageResponse,
    PollCreate, PollResponse, PollOptionResponse, PollVoteRequest,
    BookmarkResponse, ShareResponse, RepostRequest
)
from ..utils.dependencies import (
    get_current_user, save_upload_file, validate_image_file,
    validate_video_file, create_pagination_metadata
)
from ..config import settings
from ..utils.time import expires_after, isoformat_utc_z, utcnow_naive, to_utc_naive

router = APIRouter(prefix="/api/posts", tags=["Posts"])


def build_post_response(post, current_user, db):
    """Helper to build a PostResponse with all computed fields."""
    poll_data = None
    if post.poll:
        total_votes = sum(opt.votes_count for opt in post.poll.options)
        user_vote = None
        if current_user:
            vote = db.query(PollVote).filter(
                PollVote.poll_id == post.poll.id,
                PollVote.user_id == current_user.id
            ).first()
            if vote:
                user_vote = vote.option_id

        options = []
        for opt in post.poll.options:
            percentage = (opt.votes_count / total_votes * 100) if total_votes > 0 else 0
            options.append(PollOptionResponse(
                id=opt.id, text=opt.text, votes_count=opt.votes_count, percentage=round(percentage, 1)
            ))

        poll_data = PollResponse(
            id=post.poll.id,
            question=post.poll.question,
            expires_at=post.poll.expires_at,
            options=options,
            total_votes=total_votes,
            user_vote=user_vote
        )

    repost_data = None
    if post.repost and not post.repost.is_deleted:
        repost_data = build_post_response(post.repost, current_user, db)

    author_data = None
    if post.author:
        profile_picture = None
        if hasattr(post.author, 'profile') and post.author.profile:
            profile_picture = post.author.profile_picture if hasattr(post.author, 'profile_picture') else None
        author_data = {
            "id": post.author.id,
            "username": post.author.username,
            "full_name": post.author.full_name,
            "profile_picture": profile_picture,
            "is_verified": post.author.is_verified,
            "followers_count": post.author.followers_count,
            "badge": getattr(post.author, 'badge', None)
        }

    is_saved = False
    if current_user:
        is_saved = db.query(Bookmark).filter(
            Bookmark.user_id == current_user.id,
            Bookmark.post_id == post.id
        ).first() is not None

    return PostResponse(
        id=post.id,
        user_id=post.user_id,
        content=post.content,
        is_scheduled=post.is_scheduled,
        scheduled_time=post.scheduled_time,
        is_published=post.is_published,
        hashtags=post.hashtags,
        post_type=getattr(post, 'post_type', 'normal'),
        repost_id=getattr(post, 'repost_id', None),
        created_at=post.created_at,
        updated_at=post.updated_at,
        images=[PostImageResponse(
            id=img.id, image_url=img.image_url, is_video=img.is_video,
            video_url=img.video_url, order=img.order
        ) for img in (post.images or [])],
        likes_count=post.likes_count,
        comments_count=post.comments_count,
        shares_count=getattr(post, 'shares_count', 0),
        author=author_data,
        is_liked=any(like.user_id == current_user.id for like in (post.likes or [])) if current_user else False,
        is_saved=is_saved,
        poll=poll_data,
        repost=repost_data
    )


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    content: str = Form(None),
    hashtags: str = Form(None),
    tagged_user_ids: str = Form(None),
    files: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new post with optional images/videos."""
    hashtag_list = [t.strip().lower() for t in hashtags.split(",")] if hashtags else None

    post = Post(
        user_id=current_user.id,
        content=content,
        hashtags=hashtag_list,
        is_published=True,
        is_scheduled=False,
        post_type='normal'
    )
    db.add(post)
    db.flush()

    # Handle file uploads
    if files:
        for idx, file in enumerate(files):
            if file and file.filename:
                if validate_image_file(file):
                    file_path = await save_upload_file(settings.UPLOAD_DIR, file, "posts")
                    post_image = PostImage(
                        post_id=post.id, image_url=file_path,
                        is_video=False, order=idx
                    )
                    db.add(post_image)
                elif validate_video_file(file):
                    file_path = await save_upload_file(settings.UPLOAD_DIR, file, "posts")
                    post_image = PostImage(
                        post_id=post.id, image_url=file_path,
                        is_video=True, video_url=file_path, order=idx
                    )
                    db.add(post_image)

    # Add tagged users
    if tagged_user_ids:
        tagged_list = [t.strip() for t in tagged_user_ids.split(",")]
        for user_id in tagged_list:
            tagged_user = db.query(User).filter(User.id == user_id).first()
            if tagged_user:
                post.tagged_users.append(tagged_user)
                notification = Notification(
                    user_id=tagged_user.id, actor_id=current_user.id,
                    type="tag", message=f"{current_user.username} tagged you in a post",
                    reference_id=post.id, reference_type="post"
                )
                db.add(notification)

    db.commit()
    db.refresh(post)
    return build_post_response(post, current_user, db)


async def upload_post_compat(
    content: str = Form(None),
    caption: str = Form(None),
    hashtags: str = Form(None),
    files: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clean alias implementation registered from aliases.py only."""
    return await create_post(content=content or caption, hashtags=hashtags, tagged_user_ids=None, files=files, current_user=current_user, db=db)


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post_json(
    request: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a text-only post from JSON payloads used by API tests and simple clients."""
    post = Post(
        user_id=current_user.id,
        content=request.content,
        hashtags=request.hashtags,
        is_published=True,
        is_scheduled=bool(request.scheduled_time),
        scheduled_time=to_utc_naive(request.scheduled_time),
        post_type='normal'
    )
    db.add(post)
    db.flush()

    if request.tagged_user_ids:
        for user_id in request.tagged_user_ids:
            tagged_user = db.query(User).filter(User.id == user_id).first()
            if tagged_user:
                post.tagged_users.append(tagged_user)
                if tagged_user.id != current_user.id:
                    db.add(Notification(
                        user_id=tagged_user.id,
                        actor_id=current_user.id,
                        type="tag",
                        message=f"{current_user.username} tagged you in a post",
                        reference_id=post.id,
                        reference_type="post"
                    ))

    db.commit()
    db.refresh(post)
    return build_post_response(post, current_user, db)


@router.post("/poll", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_poll_post(
    request: PollCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a post with a poll."""
    post = Post(
        user_id=current_user.id,
        content=request.question,
        is_published=True,
        post_type='poll'
    )
    db.add(post)
    db.flush()

    expires_at = None
    if request.expires_hours:
        expires_at = expires_after(request.expires_hours)

    poll = Poll(
        post_id=post.id,
        question=request.question,
        expires_at=expires_at
    )
    db.add(poll)
    db.flush()

    for option_text in request.options:
        option = PollOption(poll_id=poll.id, text=option_text)
        db.add(option)

    db.commit()
    db.refresh(post)
    return build_post_response(post, current_user, db)


@router.post("/{post_id}/vote")
def vote_poll(
    post_id: str,
    request: PollVoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Vote on a poll."""
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post or not post.poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Check if already voted
    existing_vote = db.query(PollVote).filter(
        PollVote.poll_id == post.poll.id,
        PollVote.user_id == current_user.id
    ).first()

    if existing_vote:
        raise HTTPException(status_code=400, detail="Already voted on this poll")

    option = db.query(PollOption).filter(PollOption.id == request.option_id).first()
    if not option or option.poll_id != post.poll.id:
        raise HTTPException(status_code=400, detail="Invalid poll option")

    vote = PollVote(
        poll_id=post.poll.id,
        option_id=request.option_id,
        user_id=current_user.id
    )
    db.add(vote)
    option.votes_count += 1
    db.commit()

    return {"message": "Vote recorded"}


@router.post("/{post_id}/repost", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def repost_post(
    post_id: str,
    request: RepostRequest = RepostRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Repost/share a post."""
    original = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not original:
        raise HTTPException(status_code=404, detail="Post not found")

    repost = Post(
        user_id=current_user.id,
        content=request.content,
        post_type='repost',
        repost_id=post_id,
        is_published=True
    )
    db.add(repost)
    db.flush()

    # Track share
    share = PostShare(user_id=current_user.id, post_id=post_id)
    db.add(share)

    # Notification
    if original.user_id != current_user.id:
        notification = Notification(
            user_id=original.user_id, actor_id=current_user.id,
            type="share", message=f"{current_user.username} shared your post",
            reference_id=post_id, reference_type="post"
        )
        db.add(notification)

    db.commit()
    db.refresh(repost)
    return build_post_response(repost, current_user, db)


@router.get("/bookmarks", response_model=dict)
def get_bookmarks(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get bookmarked posts."""
    offset = (page - 1) * page_size
    total = db.query(Bookmark).filter(Bookmark.user_id == current_user.id).count()

    bookmarks = db.query(Bookmark).filter(
        Bookmark.user_id == current_user.id
    ).order_by(Bookmark.created_at.desc()).offset(offset).limit(page_size).all()

    post_responses = []
    for bm in bookmarks:
        post = db.query(Post).filter(Post.id == bm.post_id, Post.is_deleted == False).first()
        if post:
            post_responses.append(build_post_response(post, current_user, db))

    return {
        "posts": post_responses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total
    }


@router.get("/saved-center", response_model=dict)
def get_saved_center(
    page: int = 1,
    page_size: int = 12,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unified saved posts center used by the frontend saved/bookmarks view."""
    offset = (page - 1) * page_size
    saved_posts = db.query(Post).join(Bookmark, Bookmark.post_id == Post.id).filter(
        Bookmark.user_id == current_user.id,
        Post.is_deleted == False,
        Post.is_published == True,
    ).order_by(Bookmark.created_at.desc()).offset(offset).limit(page_size).all()
    total_posts = db.query(Bookmark).join(Post, Bookmark.post_id == Post.id).filter(
        Bookmark.user_id == current_user.id,
        Post.is_deleted == False,
    ).count()
    return {
        "posts": [build_post_response(post, current_user, db) for post in saved_posts],
        "total_posts": total_posts,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total_posts,
    }


@router.post("/{post_id}/bookmark")
def toggle_bookmark(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bookmark/unbookmark a post."""
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = db.query(Bookmark).filter(
        Bookmark.user_id == current_user.id,
        Bookmark.post_id == post_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"id": "", "post_id": post_id, "created_at": isoformat_utc_z(utcnow_naive()), "removed": True}

    bookmark = Bookmark(user_id=current_user.id, post_id=post_id)
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark


@router.get("/{post_id}/share-count")
def get_share_count(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get share count for a post."""
    count = db.query(PostShare).filter(PostShare.post_id == post_id).count()
    return {"shares_count": count}


@router.get("", response_model=dict)
def get_feed(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feed posts from followed users."""
    followed_ids = db.query(Follower.following_id).filter(
        Follower.follower_id == current_user.id,
        Follower.is_pending == False
    ).all()
    followed_ids = [f[0] for f in followed_ids]
    followed_ids.append(current_user.id)

    offset = (page - 1) * page_size
    total = db.query(Post).filter(
        Post.user_id.in_(followed_ids),
        Post.is_published == True,
        Post.is_deleted == False
    ).count()

    posts = db.query(Post).filter(
        Post.user_id.in_(followed_ids),
        Post.is_published == True,
        Post.is_deleted == False
    ).order_by(Post.created_at.desc()).offset(offset).limit(page_size).all()

    post_responses = [build_post_response(post, current_user, db) for post in posts]

    return {
        "posts": post_responses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total
    }


@router.get("/premium/feed", response_model=dict)
def get_premium_feed(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ranked premium home feed: followed posts + trending public posts without removing the old chronological feed."""
    followed_ids = [row[0] for row in db.query(Follower.following_id).filter(
        Follower.follower_id == current_user.id,
        Follower.is_pending == False
    ).all()]
    followed_ids.append(current_user.id)
    offset = (page - 1) * page_size
    posts = db.query(Post).outerjoin(Like).outerjoin(Comment).filter(
        Post.is_published == True,
        Post.is_deleted == False,
    ).group_by(Post.id).order_by(
        (func.count(Like.id) + func.count(Comment.id) * 2).desc(),
        Post.created_at.desc()
    ).offset(offset).limit(page_size).all()
    total = db.query(Post).filter(Post.is_published == True, Post.is_deleted == False).count()
    return {
        "posts": [build_post_response(post, current_user, db) for post in posts],
        "following_ids": followed_ids,
        "ranking": "engagement_then_recency",
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total,
    }


@router.get("/explore", response_model=dict)
def get_explore_posts(
    page: int = 1,
    page_size: int = 18,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Explore grid data using real local posts and hashtags."""
    offset = (page - 1) * page_size
    posts = db.query(Post).outerjoin(Like).outerjoin(Comment).filter(
        Post.is_published == True,
        Post.is_deleted == False,
    ).group_by(Post.id).order_by(
        (func.count(Like.id) + func.count(Comment.id)).desc(),
        Post.created_at.desc()
    ).offset(offset).limit(page_size).all()
    hashtags = {}
    for post in db.query(Post).filter(Post.is_published == True, Post.is_deleted == False).limit(200).all():
        for tag in post.hashtags or []:
            clean = str(tag).strip().replace("#", "")
            if clean:
                hashtags[clean] = hashtags.get(clean, 0) + 1
    return {
        "posts": [build_post_response(post, current_user, db) for post in posts],
        "hashtags": [{"tag": tag, "count": count} for tag, count in sorted(hashtags.items(), key=lambda item: item[1], reverse=True)[:20]],
        "page": page,
        "page_size": page_size,
        "has_next": len(posts) == page_size,
    }


@router.get("/user/{user_id}", response_model=dict)
def get_user_posts(
    user_id: str,
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get posts by a specific user."""
    offset = (page - 1) * page_size
    total = db.query(Post).filter(
        Post.user_id == user_id,
        Post.is_published == True,
        Post.is_deleted == False
    ).count()

    posts = db.query(Post).filter(
        Post.user_id == user_id,
        Post.is_published == True,
        Post.is_deleted == False
    ).order_by(Post.created_at.desc()).offset(offset).limit(page_size).all()

    post_responses = [build_post_response(post, current_user, db) for post in posts]

    return {
        "posts": post_responses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total
    }


@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single post by ID."""
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return build_post_response(post, current_user, db)


@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: str,
    request: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a post."""
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == current_user.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or not authorized")

    if request.content is not None:
        post.content = request.content
    if request.hashtags is not None:
        post.hashtags = request.hashtags

    db.commit()
    db.refresh(post)
    return build_post_response(post, current_user, db)


@router.delete("/{post_id}")
def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete a post. Owner only, admin can delete any."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can delete only your own post")

    post.is_deleted = True
    post.deleted_at = utcnow_naive()
    db.commit()
    return {"message": "Post deleted successfully"}