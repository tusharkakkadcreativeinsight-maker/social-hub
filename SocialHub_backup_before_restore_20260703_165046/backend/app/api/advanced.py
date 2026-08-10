import os
import zipfile
from datetime import datetime
from typing import List, Optional

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
)
from ..utils.dependencies import (
    get_admin_user,
    get_current_user,
    save_upload_file,
    validate_audio_file,
    validate_image_file,
)

router = APIRouter(tags=["Advanced Features"])


class CaptionRequest(BaseModel):
    title: Optional[str] = ""
    description: Optional[str] = ""
    category: Optional[str] = ""


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


@router.post("/api/ai/caption")
def generate_caption(payload: CaptionRequest, current_user: User = Depends(get_current_user)):
    """Generate AI caption/hashtags. Uses local fallback when OpenAI is unavailable."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_caption(payload.title, payload.description, payload.category)

    # Keep OpenAI optional so the app never fails when the SDK/network is unavailable.
    try:
        from openai import OpenAI  # type: ignore

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
    reel.updated_at = datetime.utcnow()
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
    chat.updated_at = datetime.utcnow()
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
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
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
