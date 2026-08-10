import os
import zipfile
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.models import (
    AuditLog,
    Chat,
    CollaborationApplication,
    CollaborationOffer,
    Comment,
    Follower,
    Like,
    MarketplaceProduct,
    Message,
    Post,
    Reel,
    ReelComment,
    ReelLike,
    Report,
    ScheduledPost,
    Story,
    StoryPoll,
    StoryPollVote,
    User,
    PostImage,
)
from ..utils.dependencies import (
    get_admin_user,
    get_current_user,
    save_upload_file,
    validate_audio_file,
    validate_image_file,
)
from ..utils.time import utcnow_naive

router = APIRouter(tags=["Advanced Features"])


class CaptionRequest(BaseModel):
    title: Optional[str] = ""
    description: Optional[str] = ""
    category: Optional[str] = ""


class HashtagRequest(BaseModel):
    keywords: str = ""
    count: Optional[int] = 10


class BioRequest(BaseModel):
    name: str = ""
    niche: str = ""
    vibe: Optional[str] = "professional"


class ReelTitleRequest(BaseModel):
    topic: str = ""
    keywords: Optional[str] = ""


class PostIdeaRequest(BaseModel):
    niche: str = ""
    count: Optional[int] = 5


class ContentCalendarRequest(BaseModel):
    niche: str = ""
    goal: Optional[str] = "growth"
    days: Optional[int] = Field(7, ge=1, le=30)


class ViralHookRequest(BaseModel):
    topic: str = ""
    audience: Optional[str] = "creators"


class CommentReplyRequest(BaseModel):
    comment: str
    tone: Optional[str] = "friendly"
    context: Optional[str] = ""


class ReelEditRequest(BaseModel):
    trim_start: Optional[float] = Field(None, ge=0)
    trim_end: Optional[float] = Field(None, ge=0)
    text_overlay: Optional[str] = Field(None, max_length=255)
    filter_name: Optional[str] = Field(None, max_length=100)
    music_name: Optional[str] = Field(None, max_length=150)


class ScheduleRequest(BaseModel):
    content: Optional[str] = ""
    media_urls: List[str] = []
    hashtags: List[str] = []
    scheduled_at: datetime
    content_type: str = "post"


class StoryPollRequest(BaseModel):
    poll_type: str = "poll"
    question: str
    options: List[str] = []
    correct_option: Optional[str] = None


class StoryVoteRequest(BaseModel):
    poll_id: Optional[str] = None
    answer: str


class GroupCreateRequest(BaseModel):
    name: str
    member_ids: List[str] = []


class GroupMessageRequest(BaseModel):
    content: Optional[str] = ""
    message_type: str = "text"


class MarketplaceProductRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    price: float = 0
    category: Optional[str] = "General"
    image_url: Optional[str] = None


class CollabRequest(BaseModel):
    title: str
    description: str
    budget: Optional[str] = None
    category: Optional[str] = None


class CollabApplyRequest(BaseModel):
    message: Optional[str] = ""


def _user_card(user: Optional[User]):
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "profile_picture": user.profile_picture,
        "is_verified": user.is_verified,
    }


def _product_card(product: MarketplaceProduct):
    return {
        "id": product.id,
        "seller_id": product.seller_id,
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "category": product.category,
        "image_url": product.image_url,
        "created_at": product.created_at,
        "seller": _user_card(product.seller),
    }


def _collab_card(offer: CollaborationOffer):
    return {
        "id": offer.id,
        "user_id": offer.user_id,
        "title": offer.title,
        "description": offer.description,
        "budget": offer.budget,
        "category": offer.category,
        "status": offer.status,
        "created_at": offer.created_at,
        "user": _user_card(offer.user),
        "applications_count": len(offer.applications),
    }


# ==================== AI FALLBACKS ====================

def _fallback_caption(title: str = "", description: str = "", category: str = ""):
    seed = " ".join([title or "", description or "", category or ""]).strip() or "new moment"
    clean_words = [w.strip("#,.!?").lower() for w in seed.split() if len(w.strip("#,.!?")) > 2]
    tags = []
    for word in clean_words[:8]:
        tag = "#" + "".join(ch for ch in word if ch.isalnum())
        if len(tag) > 1 and tag not in tags:
            tags.append(tag)
    tags += ["#SocialHub", "#Creator", "#Trending"]
    tags = tags[:10]
    caption = f"Sharing {seed[:80]} ✨\n\nWhat do you think?"
    return {"caption": caption, "hashtags": tags, "source": "local_fallback"}


def _fallback_hashtags(keywords: str = "", count: int = 10):
    words = [w.strip().lower() for w in keywords.replace(",", " ").split() if len(w.strip()) > 2]
    tags = []
    for word in words[:8]:
        tag = "#" + "".join(ch for ch in word if ch.isalnum())
        if len(tag) > 1 and tag not in tags:
            tags.append(tag)
    defaults = ["#SocialHub", "#Creator", "#Trending", "#Viral", "#Explore", "#Reach", "#New", "#InstaDaily"]
    for t in defaults:
        if t not in tags:
            tags.append(t)
        if len(tags) >= count:
            break
    return {"hashtags": tags[:count], "source": "local_fallback"}


def _fallback_bio(name: str = "", niche: str = "", vibe: str = "professional"):
    samples = [
        f"{name} | {niche.title() if niche else 'Creator'}\n✨ Sharing my journey\n📩 Collabs: DM me\n⬇️ Check out my latest",
        f"👋 Hey, I'm {name}!\n{'🎯 ' + niche.title() if niche else ''}\n🚀 Building in public\n💬 Let's connect!",
        f"{name} • {niche.title() if niche else 'Creator'}\n🌟 Living my best life\n📸 Capturing moments\n👇 Follow for more",
    ]
    return {"bio": samples[hash(name or "") % len(samples)], "source": "local_fallback"}


def _fallback_reel_title(topic: str = "", keywords: str = ""):
    titles = [
        f"POV: {topic or 'You finally'} 🎬",
        f"{topic or 'This'} is INSANE 🔥",
        f"The Ultimate {topic or 'Vibe'} 🚀",
        f"{topic or 'New'} Era Begins ✨",
        f"You Won't Believe This {topic or 'Moment'} 😱",
    ]
    return {"titles": titles, "source": "local_fallback"}


def _fallback_post_ideas(niche: str = "", count: int = 5):
    generic = [
        "Top 10 tips for beginners",
        "Behind the scenes: my workflow",
        "The story of how I started",
        "Q&A: Answering your top questions",
        "My favorite tools and resources",
        "How I stay motivated daily",
        "Common mistakes to avoid",
        "Day in the life vlog",
        "My biggest lesson learned",
        "What nobody tells you about this journey",
    ]
    if niche:
        ideas = [f"{niche.title()} tip #{i+1}: {generic[i % len(generic)]}" for i in range(count)]
    else:
        ideas = generic[:count]
    return {"ideas": ideas, "source": "local_fallback"}


def _fallback_calendar(niche: str = "", goal: str = "growth", days: int = 7):
    pillars = ["educate", "behind-the-scenes", "community", "story", "offer", "trend", "recap"]
    plan = []
    for i in range(days):
        date = (utcnow_naive() + timedelta(days=i)).date().isoformat()
        pillar = pillars[i % len(pillars)]
        topic = niche.title() if niche else "Creator"
        plan.append({
            "date": date,
            "type": ["post", "reel", "story"][i % 3],
            "pillar": pillar,
            "idea": f"{topic} {pillar.replace('-', ' ')} content for {goal}",
            "cta": "Save this and share with a friend" if i % 2 == 0 else "Comment your biggest question",
        })
    return {"calendar": plan, "source": "local_fallback"}


def _fallback_hooks(topic: str = "", audience: str = "creators"):
    base = topic or "your next post"
    hooks = [
        f"Stop scrolling if you want better results with {base}",
        f"Nobody tells {audience} this about {base}",
        f"I tried {base} for 7 days — here is what changed",
        f"3 mistakes that are quietly hurting your {base}",
        f"Steal my simple framework for {base}",
        f"Before you post about {base}, watch this",
    ]
    return {"hooks": hooks, "source": "local_fallback"}


def _fallback_comment_reply(comment: str, tone: str = "friendly", context: str = ""):
    tone_prefix = {
        "professional": "Thanks for sharing your perspective —",
        "funny": "Haha, I love this 😂",
        "supportive": "I appreciate you saying that!",
        "friendly": "Thanks so much!",
    }.get((tone or "friendly").lower(), "Thanks so much!")
    reply = f"{tone_prefix} {comment[:120]}" if tone == "professional" else f"{tone_prefix} Really appreciate your comment."
    if context:
        reply += f" I’ll share more about {context[:80]} soon."
    return {"reply": reply, "alternatives": [reply, "Great point — thanks for being here!", "Love this feedback, thank you 🙌"], "source": "local_fallback"}


def _try_openai(prompt: str, fallback_func, *args):
    """Try OpenAI API, return fallback on failure."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback_func(*args)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        text = completion.choices[0].message.content or ""
        result = fallback_func(*args)
        result["ai_text"] = text
        result["source"] = "openai"
        return result
    except Exception:
        return fallback_func(*args)


# ==================== AI ENDPOINTS ====================

@router.post("/api/ai/caption")
def generate_caption(payload: CaptionRequest, current_user: User = Depends(get_current_user)):
    """Generate AI caption/hashtags. Uses local fallback when OpenAI is unavailable."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_caption(payload.title, payload.description, payload.category)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = (
            "Create a modern social media caption and 8 hashtags as JSON with keys "
            f"caption and hashtags for title={payload.title!r}, "
            f"description={payload.description!r}, category={payload.category!r}."
        )
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        text = completion.choices[0].message.content or ""
        fallback = _fallback_caption(payload.title, payload.description, payload.category)
        fallback["ai_text"] = text
        fallback["source"] = "openai"
        return fallback
    except Exception:
        return _fallback_caption(payload.title, payload.description, payload.category)


@router.post("/api/ai/hashtags")
def generate_hashtags(payload: HashtagRequest, current_user: User = Depends(get_current_user)):
    """Generate AI hashtags based on keywords."""
    prompt = (
        f"Generate {payload.count} social media hashtags for keywords: {payload.keywords}. "
        "Return as a JSON array of strings."
    )
    return _try_openai(prompt, _fallback_hashtags, payload.keywords, payload.count)


@router.post("/api/ai/bio")
def generate_bio(payload: BioRequest, current_user: User = Depends(get_current_user)):
    """Generate AI bio text."""
    prompt = (
        f"Write a compelling social media bio for someone named {payload.name} "
        f"in the {payload.niche} niche. Tone: {payload.vibe}. Return as plain text."
    )
    return _try_openai(prompt, _fallback_bio, payload.name, payload.niche, payload.vibe)


@router.post("/api/ai/reel-title")
def generate_reel_title(payload: ReelTitleRequest, current_user: User = Depends(get_current_user)):
    """Generate AI reel title ideas."""
    prompt = (
        f"Generate 5 attention-grabbing reel title ideas about {payload.topic}. "
        f"Keywords: {payload.keywords}. Return as a JSON array of strings."
    )
    return _try_openai(prompt, _fallback_reel_title, payload.topic, payload.keywords)


@router.post("/api/ai/post-ideas")
def generate_post_ideas(payload: PostIdeaRequest, current_user: User = Depends(get_current_user)):
    """Generate AI post ideas for a niche."""
    prompt = (
        f"Generate {payload.count} creative post ideas for the {payload.niche} niche. "
        "Return as a JSON array of strings."
    )
    return _try_openai(prompt, _fallback_post_ideas, payload.niche, payload.count)


@router.post("/api/ai/content-calendar")
def generate_content_calendar(payload: ContentCalendarRequest, current_user: User = Depends(get_current_user)):
    prompt = f"Create a {payload.days}-day content calendar for a {payload.niche} creator focused on {payload.goal}. Return JSON."
    return _try_openai(prompt, _fallback_calendar, payload.niche, payload.goal, payload.days)


@router.post("/api/ai/viral-hooks")
def generate_viral_hooks(payload: ViralHookRequest, current_user: User = Depends(get_current_user)):
    prompt = f"Generate 8 viral short-form video hooks about {payload.topic} for {payload.audience}. Return JSON array."
    return _try_openai(prompt, _fallback_hooks, payload.topic, payload.audience)


@router.post("/api/ai/comment-reply")
def generate_comment_reply(payload: CommentReplyRequest, current_user: User = Depends(get_current_user)):
    prompt = f"Write 3 {payload.tone} replies to this social media comment: {payload.comment}. Context: {payload.context}. Return JSON."
    return _try_openai(prompt, _fallback_comment_reply, payload.comment, payload.tone, payload.context)


# ==================== EXISTING ENDPOINTS ====================

@router.post("/api/reels/{reel_id}/edit")
def edit_reel(reel_id: str, payload: ReelEditRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reel = db.query(Reel).filter(Reel.id == reel_id, Reel.is_deleted == False).first()
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    if reel.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to edit this reel")
    if payload.trim_end is not None and payload.trim_start is not None and payload.trim_end <= payload.trim_start:
        raise HTTPException(status_code=400, detail="trim_end must be greater than trim_start")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reel, field, value)
    reel.edit_metadata = payload.model_dump(exclude_none=True)
    reel.updated_at = utcnow_naive()
    db.commit()
    return {"message": "Reel edit metadata saved", "reel_id": reel.id, "metadata": reel.edit_metadata}


@router.post("/api/schedule/post", status_code=status.HTTP_201_CREATED)
def schedule_post(payload: ScheduleRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.content_type not in {"post", "reel", "story"}:
        raise HTTPException(status_code=400, detail="content_type must be post, reel, or story")
    scheduled = ScheduledPost(
        user_id=current_user.id,
        content=payload.content,
        media_urls=payload.media_urls,
        hashtags=payload.hashtags,
        scheduled_at=payload.scheduled_at,
        content_type=payload.content_type,
        status="pending",
    )
    db.add(scheduled)
    db.commit()
    db.refresh(scheduled)
    return {"message": "Scheduled successfully", "item": scheduled}


def publish_due_scheduled_content(db: Session, limit: int = 50):
    """Publish due scheduled SocialHub content without requiring Celery."""
    due_items = db.query(ScheduledPost).filter(
        ScheduledPost.status == "pending",
        ScheduledPost.scheduled_at <= utcnow_naive(),
        ScheduledPost.platform == "socialhub",
    ).order_by(ScheduledPost.scheduled_at.asc()).limit(limit).all()
    published = []
    failed = []
    for item in due_items:
        try:
            if item.content_type == "post":
                post = Post(user_id=item.user_id, content=item.content, hashtags=item.hashtags, is_published=True)
                db.add(post)
                db.flush()
                for idx, media_url in enumerate(item.media_urls or []):
                    is_video = str(media_url).lower().endswith((".mp4", ".mov", ".webm", ".avi"))
                    db.add(PostImage(post_id=post.id, image_url=media_url, video_url=media_url if is_video else None, is_video=is_video, order=idx))
            elif item.content_type == "reel":
                media_url = (item.media_urls or [None])[0]
                if not media_url:
                    raise ValueError("A scheduled reel requires a media URL")
                db.add(Reel(user_id=item.user_id, video_url=media_url, caption=item.content, hashtags=item.hashtags))
            elif item.content_type == "story":
                media_url = (item.media_urls or [None])[0]
                if not media_url:
                    raise ValueError("A scheduled story requires a media URL")
                media_type = "video" if str(media_url).lower().endswith((".mp4", ".mov", ".webm", ".avi")) else "image"
                db.add(Story(user_id=item.user_id, media_url=media_url, media_type=media_type, caption=item.content, expires_at=utcnow_naive() + timedelta(hours=24)))
            else:
                raise ValueError("Unsupported content type")
            item.status = "published"
            item.published_at = utcnow_naive()
            published.append(item.id)
        except Exception as exc:
            item.status = "failed"
            failed.append({"id": item.id, "error": str(exc)})
    db.commit()
    return {"published_count": len(published), "published_ids": published, "failed": failed}


@router.get("/api/schedule/me")
def get_my_schedule(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(ScheduledPost).filter(ScheduledPost.user_id == current_user.id).order_by(ScheduledPost.scheduled_at.desc()).all()
    return {"items": items, "total": len(items)}


@router.delete("/api/schedule/{schedule_id}")
def delete_schedule(schedule_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(ScheduledPost).filter(ScheduledPost.id == schedule_id, ScheduledPost.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Scheduled item not found")
    db.delete(item)
    db.commit()
    return {"message": "Scheduled item deleted"}


@router.post("/api/schedule/{schedule_id}/cancel")
def cancel_schedule(schedule_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(ScheduledPost).filter(ScheduledPost.id == schedule_id, ScheduledPost.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Scheduled item not found")
    if item.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending scheduled content can be cancelled")
    item.status = "cancelled"
    db.commit()
    return {"message": "Scheduled item cancelled"}


@router.post("/api/schedule/publish-due")
def publish_due_now(current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return publish_due_scheduled_content(db)


@router.get("/api/creator/dashboard")
def creator_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post_ids = [p.id for p in db.query(Post.id).filter(Post.user_id == current_user.id, Post.is_deleted == False).all()]
    reel_ids = [r.id for r in db.query(Reel.id).filter(Reel.user_id == current_user.id, Reel.is_deleted == False).all()]
    total_posts = len(post_ids)
    total_reels = len(reel_ids)
    likes = db.query(Like).filter(Like.post_id.in_(post_ids)).count() if post_ids else 0
    comments = db.query(Comment).filter(Comment.post_id.in_(post_ids), Comment.is_deleted == False).count() if post_ids else 0
    reel_likes = db.query(ReelLike).filter(ReelLike.reel_id.in_(reel_ids)).count() if reel_ids else 0
    reel_comments = db.query(ReelComment).filter(ReelComment.reel_id.in_(reel_ids), ReelComment.is_deleted == False).count() if reel_ids else 0
    views = db.query(func.coalesce(func.sum(Reel.views_count), 0)).filter(Reel.user_id == current_user.id).scalar() or 0
    followers = db.query(Follower).filter(Follower.following_id == current_user.id, Follower.is_pending == False).count()
    following = db.query(Follower).filter(Follower.follower_id == current_user.id, Follower.is_pending == False).count()
    engagement = round(((likes + comments + reel_likes + reel_comments) / max(followers, 1)) * 100, 2)
    best_posts = db.query(Post).filter(Post.user_id == current_user.id, Post.is_deleted == False).all()
    best_reels = db.query(Reel).filter(Reel.user_id == current_user.id, Reel.is_deleted == False).all()
    best_content = []
    for post in best_posts:
        best_content.append({"id": post.id, "type": "post", "title": (post.content or "Post")[:80], "score": post.likes_count + post.comments_count, "likes": post.likes_count, "comments": post.comments_count, "views": 0})
    for reel in best_reels:
        best_content.append({"id": reel.id, "type": "reel", "title": (reel.caption or "Reel")[:80], "score": reel.likes_count + reel.comments_count + int((reel.views_count or 0) / 100), "likes": reel.likes_count, "comments": reel.comments_count, "views": reel.views_count})
    best_content = sorted(best_content, key=lambda item: item["score"], reverse=True)[:5]
    return {
        "total_posts": total_posts,
        "total_reels": total_reels,
        "followers": followers,
        "following": following,
        "likes": likes + reel_likes,
        "comments": comments + reel_comments,
        "views": int(views),
        "engagement_rate": engagement,
        "chart": [total_posts, total_reels, likes + reel_likes, comments + reel_comments, int(views)],
        "best_content": best_content,
    }


# ==================== CREATOR ANALYTICS ====================

@router.get("/api/creator/analytics")
def creator_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get detailed creator analytics."""
    post_ids = [p.id for p in db.query(Post.id).filter(Post.user_id == current_user.id, Post.is_deleted == False).all()]
    reel_ids = [r.id for r in db.query(Reel.id).filter(Reel.user_id == current_user.id, Reel.is_deleted == False).all()]
    total_posts = len(post_ids)
    total_reels = len(reel_ids)
    total_likes = db.query(Like).filter(Like.post_id.in_(post_ids)).count() if post_ids else 0
    total_comments = db.query(Comment).filter(Comment.post_id.in_(post_ids), Comment.is_deleted == False).count() if post_ids else 0
    total_reel_likes = db.query(ReelLike).filter(ReelLike.reel_id.in_(reel_ids)).count() if reel_ids else 0
    total_reel_comments = db.query(ReelComment).filter(ReelComment.reel_id.in_(reel_ids), ReelComment.is_deleted == False).count() if reel_ids else 0
    total_reel_views = db.query(func.coalesce(func.sum(Reel.views_count), 0)).filter(Reel.user_id == current_user.id).scalar() or 0
    followers_count = db.query(Follower).filter(Follower.following_id == current_user.id, Follower.is_pending == False).count()
    following_count = db.query(Follower).filter(Follower.follower_id == current_user.id, Follower.is_pending == False).count()
    total_engagements = total_likes + total_comments + total_reel_likes + total_reel_comments
    engagement_rate = round((total_engagements / max(followers_count, 1)) * 100, 2)

    best_posts = db.query(Post).filter(Post.user_id == current_user.id, Post.is_deleted == False).all()
    best_reels = db.query(Reel).filter(Reel.user_id == current_user.id, Reel.is_deleted == False).all()
    best_performing_posts = sorted(
        [{"id": p.id, "content": (p.content or "")[:100], "likes": p.likes_count, "comments": p.comments_count, "score": p.likes_count + p.comments_count} for p in best_posts],
        key=lambda x: x["score"], reverse=True
    )[:5]
    best_performing_reels = sorted(
        [{"id": r.id, "caption": (r.caption or "")[:100], "likes": r.likes_count, "comments": r.comments_count, "views": r.views_count, "score": r.likes_count + r.comments_count + int((r.views_count or 0) / 10)} for r in best_reels],
        key=lambda x: x["score"], reverse=True
    )[:5]

    return {
        "total_posts": total_posts,
        "total_reels": total_reels,
        "total_likes": total_likes + total_reel_likes,
        "total_comments": total_comments + total_reel_comments,
        "total_reel_views": int(total_reel_views),
        "followers_count": followers_count,
        "following_count": following_count,
        "engagement_rate": engagement_rate,
        "best_performing_posts": best_performing_posts,
        "best_performing_reels": best_performing_reels,
    }


# ==================== SMART EXPLORE FEED ====================

def _explore_payload(current_user: User, db: Session):
    """Get smart explore feed with trending content."""
    # Trending posts (based on likes, comments, shares, recency)
    trending_posts_query = db.query(Post).filter(
        Post.is_deleted == False, Post.is_published == True
    ).order_by(Post.created_at.desc()).limit(80).all()
    trending_posts_query = sorted(trending_posts_query, key=lambda p: (p.likes_count * 2 + p.comments_count * 3 + p.shares_count * 4, p.created_at), reverse=True)[:20]

    trending_posts = []
    for p in trending_posts_query:
        author_data = None
        if p.author:
            author_data = {
                "id": p.author.id, "username": p.author.username,
                "full_name": p.author.full_name,
                "profile_picture": p.author.profile_picture,
                "is_verified": p.author.is_verified,
            }
        trending_posts.append({
            "id": p.id, "user_id": p.user_id, "content": (p.content or "")[:200],
            "likes_count": p.likes_count, "comments_count": p.comments_count,
            "shares_count": p.shares_count, "created_at": p.created_at,
            "author": author_data,
            "images": [{"image_url": img.image_url, "is_video": img.is_video, "video_url": img.video_url} for img in p.images[:3]],
        })

    # Trending reels (based on views, likes, comments)
    trending_reels_query = db.query(Reel).filter(
        Reel.is_deleted == False
    ).order_by(Reel.created_at.desc()).limit(80).all()
    trending_reels_query = sorted(trending_reels_query, key=lambda r: ((r.views_count or 0) + r.likes_count * 3 + r.comments_count * 4, r.created_at), reverse=True)[:20]

    trending_reels = []
    for r in trending_reels_query:
        author_data = None
        if r.user:
            author_data = {
                "id": r.user.id, "username": r.user.username,
                "full_name": r.user.full_name,
                "profile_picture": r.user.profile_picture,
                "is_verified": r.user.is_verified,
            }
        trending_reels.append({
            "id": r.id, "user_id": r.user_id, "video_url": r.video_url,
            "caption": (r.caption or "")[:150], "views_count": r.views_count,
            "likes_count": r.likes_count, "comments_count": r.comments_count,
            "created_at": r.created_at, "author": author_data,
        })

    # Trending hashtags (process in Python for SQLite compatibility)
    hashtag_count = {}
    posts_with_tags = db.query(Post.hashtags).filter(
        Post.is_deleted == False, Post.hashtags.isnot(None)
    ).limit(500).all()
    for row in posts_with_tags:
        tags = row[0] if hasattr(row, '__getitem__') else row.hashtags
        if tags and isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str) and tag.strip():
                    hashtag_count[tag.strip().lower()] = hashtag_count.get(tag.strip().lower(), 0) + 1
    
    trending_hashtags_list = sorted(
        [{"tag": tag, "count": count} for tag, count in hashtag_count.items()],
        key=lambda x: x["count"], reverse=True
    )[:15]

    # Suggested users (verified users first, then by followers count)
    suggested_users = db.query(User).filter(
        User.is_banned == False, User.id != current_user.id
    ).order_by(User.is_verified.desc(), User.created_at.desc()).limit(30).all()
    suggested_users = sorted(suggested_users, key=lambda u: (u.is_verified, u.followers_count), reverse=True)[:10]

    suggested_users_list = []
    for u in suggested_users:
        suggested_users_list.append({
            "id": u.id, "username": u.username,
            "full_name": u.full_name,
            "profile_picture": u.profile_picture,
            "is_verified": u.is_verified,
            "followers_count": u.followers_count,
        })

    return {
        "trending_posts": trending_posts,
        "trending_reels": trending_reels,
        "trending_hashtags": trending_hashtags_list,
        "suggested_users": suggested_users_list,
    }


@router.get("/api/explore")
def explore_feed(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get smart explore feed with trending content."""
    return _explore_payload(current_user, db)


@router.get("/api/explore/recommended")
def explore_recommended(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Recommendation engine endpoint for posts, reels, hashtags, and creators."""
    payload = _explore_payload(current_user, db)
    followed_ids = [row[0] for row in db.query(Follower.following_id).filter(Follower.follower_id == current_user.id, Follower.is_pending == False).all()]
    payload["recommended_posts"] = payload["trending_posts"]
    payload["recommended_reels"] = payload["trending_reels"]
    payload["signals"] = {"followed_users": followed_ids, "uses_likes": True, "uses_comments": True, "uses_reel_views": True, "uses_hashtags": True, "uses_recency": True}
    return payload


# ==================== STORY POLLS ====================

@router.post("/api/stories/{story_id}/poll", status_code=status.HTTP_201_CREATED)
def create_story_poll(story_id: str, payload: StoryPollRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id, Story.is_deleted == False).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only story owner can add polls")
    poll = StoryPoll(
        story_id=story_id,
        user_id=current_user.id,
        poll_type=payload.poll_type,
        question=payload.question,
        options=payload.options,
        correct_option=payload.correct_option,
    )
    db.add(poll)
    db.commit()
    db.refresh(poll)
    return {"message": "Story interaction added", "poll": poll}


@router.post("/api/stories/{story_id}/vote")
def vote_story_poll(story_id: str, payload: StoryVoteRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(StoryPoll).filter(StoryPoll.story_id == story_id)
    poll = query.filter(StoryPoll.id == payload.poll_id).first() if payload.poll_id else query.order_by(StoryPoll.created_at.desc()).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Story poll not found")
    existing = db.query(StoryPollVote).filter(StoryPollVote.poll_id == poll.id, StoryPollVote.user_id == current_user.id).first()
    if existing:
        existing.answer = payload.answer
    else:
        db.add(StoryPollVote(poll_id=poll.id, story_id=story_id, user_id=current_user.id, answer=payload.answer))
    db.commit()
    return {"message": "Vote saved"}


@router.get("/api/stories/{story_id}/results")
def story_poll_results(story_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    polls = db.query(StoryPoll).filter(StoryPoll.story_id == story_id).all()
    return {
        "polls": [
            {
                "id": poll.id,
                "poll_type": poll.poll_type,
                "question": poll.question,
                "options": poll.options,
                "total_votes": len(poll.votes),
                "results": {option: sum(1 for v in poll.votes if v.answer == option) for option in (poll.options or [])},
                "answers": [v.answer for v in poll.votes] if poll.poll_type == "question" else [],
            }
            for poll in polls
        ]
    }


# ==================== CHAT GROUPS ====================

@router.post("/api/chat/groups", status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = Chat(name=payload.name, is_group=True, created_by=current_user.id)
    db.add(chat)
    db.flush()
    member_ids = set(payload.member_ids + [current_user.id])
    for user in db.query(User).filter(User.id.in_(member_ids)).all():
        chat.participants.append(user)
    db.commit()
    db.refresh(chat)
    return {"message": "Group created", "group": {"id": chat.id, "name": chat.name, "participants": [_user_card(u) for u in chat.participants]}}


@router.get("/api/chat/groups")
def list_groups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    groups = db.query(Chat).filter(Chat.is_group == True, Chat.participants.any(User.id == current_user.id)).order_by(Chat.updated_at.desc()).all()
    return {"groups": [{"id": g.id, "name": g.name, "participants": [_user_card(u) for u in g.participants]} for g in groups]}


@router.post("/api/chat/groups/{group_id}/messages")
def send_group_message(group_id: str, payload: GroupMessageRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == group_id, Chat.is_group == True).first()
    if not chat or current_user.id not in [p.id for p in chat.participants]:
        raise HTTPException(status_code=404, detail="Group not found")
    msg = Message(chat_id=group_id, sender_id=current_user.id, content=payload.content, message_type=payload.message_type)
    chat.updated_at = utcnow_naive()
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"message": "Message sent", "item": msg}


@router.post("/api/chat/groups/{group_id}/files")
async def send_group_file(group_id: str, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == group_id, Chat.is_group == True).first()
    if not chat or current_user.id not in [p.id for p in chat.participants]:
        raise HTTPException(status_code=404, detail="Group not found")
    content_type = file.content_type or ""
    msg_type = "voice" if validate_audio_file(file) else "image" if content_type.startswith("image") else "video" if content_type.startswith("video") else "file"
    file_path = await save_upload_file(settings.UPLOAD_DIR, file, "chat_files")
    msg = Message(chat_id=group_id, sender_id=current_user.id, content=file.filename, message_type=msg_type, file_url=file_path)
    db.add(msg)
    db.commit()
    return {"message": "File sent", "item": msg}


# ==================== MARKETPLACE ====================

@router.post("/api/marketplace/products", status_code=status.HTTP_201_CREATED)
async def create_product(
    title: str = Form(...),
    description: str = Form(""),
    price: float = Form(0),
    category: str = Form("General"),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    image_url = None
    if image:
        if not validate_image_file(image):
            raise HTTPException(status_code=400, detail="Invalid product image")
        image_url = await save_upload_file(settings.UPLOAD_DIR, image, "marketplace")
    product = MarketplaceProduct(seller_id=current_user.id, title=title, description=description, price=price, category=category, image_url=image_url)
    db.add(product)
    db.commit()
    db.refresh(product)
    return {"message": "Product created", "product": product}


@router.get("/api/marketplace/products")
def list_products(db: Session = Depends(get_db)):
    products = db.query(MarketplaceProduct).filter(MarketplaceProduct.is_deleted == False).order_by(MarketplaceProduct.created_at.desc()).all()
    return {"products": [_product_card(p) for p in products]}


@router.get("/api/marketplace/products/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(MarketplaceProduct).filter(MarketplaceProduct.id == product_id, MarketplaceProduct.is_deleted == False).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product": _product_card(product)}


@router.delete("/api/marketplace/products/{product_id}")
def delete_product(product_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.query(MarketplaceProduct).filter(MarketplaceProduct.id == product_id).first()
    if not product or (product.seller_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_deleted = True
    db.commit()
    return {"message": "Product removed"}


# ==================== COLLABS ====================

@router.post("/api/collabs", status_code=status.HTTP_201_CREATED)
def create_collab(payload: CollabRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    offer = CollaborationOffer(user_id=current_user.id, title=payload.title, description=payload.description, budget=payload.budget, category=payload.category)
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return {"message": "Collaboration offer posted", "offer": offer}


@router.get("/api/collabs")
def list_collabs(db: Session = Depends(get_db)):
    offers = db.query(CollaborationOffer).filter(CollaborationOffer.status == "open").order_by(CollaborationOffer.created_at.desc()).all()
    return {"offers": [_collab_card(o) for o in offers]}


@router.post("/api/collabs/{offer_id}/apply")
def apply_collab(offer_id: str, payload: CollabApplyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    offer = db.query(CollaborationOffer).filter(CollaborationOffer.id == offer_id, CollaborationOffer.status == "open").first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    existing = db.query(CollaborationApplication).filter(CollaborationApplication.offer_id == offer_id, CollaborationApplication.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already applied")
    app = CollaborationApplication(offer_id=offer_id, user_id=current_user.id, message=payload.message)
    db.add(app)
    db.commit()
    return {"message": "Application submitted"}


# ==================== ADMIN ENDPOINTS ====================

@router.get("/api/admin/stats")
def admin_stats(current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return {
        "users": db.query(User).count(),
        "posts": db.query(Post).filter(Post.is_deleted == False).count(),
        "reels": db.query(Reel).filter(Reel.is_deleted == False).count(),
        "stories": db.query(Story).filter(Story.is_deleted == False).count(),
        "reports": db.query(Report).count(),
        "marketplace_products": db.query(MarketplaceProduct).filter(MarketplaceProduct.is_deleted == False).count(),
        "collabs": db.query(CollaborationOffer).count(),
    }


@router.post("/api/admin/users/{user_id}/verify")
def verify_user(user_id: str, current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    user.badge = user.badge or "verified"
    db.add(AuditLog(admin_id=current_user.id, action="verified user", target_type="user", target_id=user_id))
    db.commit()
    return {"message": "User verified"}


@router.post("/api/admin/users/{user_id}/ban")
def post_ban_user(user_id: str, is_banned: bool = True, current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot ban admin users")
    user.is_banned = is_banned
    db.add(AuditLog(admin_id=current_user.id, action="banned user" if is_banned else "unbanned user", target_type="user", target_id=user_id))
    db.commit()
    return {"message": "User banned" if is_banned else "User unbanned"}


@router.post("/api/admin/remove/{target_type}/{target_id}")
def admin_remove_content(target_type: str, target_id: str, current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    model_map = {"post": Post, "reel": Reel, "story": Story, "comment": Comment}
    model = model_map.get(target_type)
    if not model:
        raise HTTPException(status_code=400, detail="Invalid target_type")
    item = db.query(model).filter(model.id == target_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    if hasattr(item, "is_deleted"):
        item.is_deleted = True
    else:
        db.delete(item)
    db.add(AuditLog(admin_id=current_user.id, action=f"removed {target_type}", target_type=target_type, target_id=target_id))
    db.commit()
    return {"message": f"{target_type} removed"}


@router.post("/api/admin/backup")
def backup_project(current_user: User = Depends(get_admin_user)):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    backups_dir = os.path.join(project_root, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    stamp = utcnow_naive().strftime("%Y%m%d_%H%M%S")
    zip_path = os.path.join(backups_dir, f"socialhub_backup_{stamp}.zip")
    db_path = settings.DATABASE_URL.replace("sqlite:///", "") if settings.DATABASE_URL.startswith("sqlite:///") else os.path.join(project_root, "socialhub.db")
    uploads_dir = settings.UPLOAD_DIR
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(db_path):
            zf.write(db_path, arcname="socialhub.db")
        if os.path.exists(uploads_dir):
            for root, _, files in os.walk(uploads_dir):
                for file in files:
                    full = os.path.join(root, file)
                    zf.write(full, arcname=os.path.relpath(full, project_root))
    return {"message": "Backup created", "backup": zip_path}