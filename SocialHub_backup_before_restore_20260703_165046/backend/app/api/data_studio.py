import uuid
import random
import string
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil

from ..database import get_db
from ..models.models import (
    User, Post, PostImage, Reel, Follower, DemoDataBatch, OriginalMediaAsset, MediaImportLog
)
from ..utils.dependencies import get_current_user
from ..utils.security import hash_password
from ..config import settings

router = APIRouter()

# ---------- CONFIG ----------
DEMO_MEDIA_DIR = os.path.join(
    settings.UPLOAD_DIR,
    "original_media"
)
os.makedirs(DEMO_MEDIA_DIR, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB

DEMO_USERNAMES = [
    "alice", "bob", "charlie", "diana", "evan", "fiona", "george", "hannah",
    "ivan", "julia", "kevin", "luna", "mason", "nina", "oscar", "priya",
    "quinn", "rachel", "steve", "tina", "uma", "victor", "wendy", "xander",
    "yara", "zack", "amber", "brian", "cindy", "derek", "elena", "felix",
    "grace", "henry", "iris", "jack", "kelly", "leo", "mia", "noah"
]
DEMO_FIRST_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Evan", "Fiona", "George", "Hannah",
    "Ivan", "Julia", "Kevin", "Luna", "Mason", "Nina", "Oscar", "Priya",
    "Quinn", "Rachel", "Steve", "Tina", "Uma", "Victor", "Wendy", "Xander",
    "Yara", "Zack", "Amber", "Brian", "Cindy", "Derek", "Elena", "Felix",
    "Grace", "Henry", "Iris", "Jack", "Kelly", "Leo", "Mia", "Noah"
]
DEMO_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
]
DEMO_CAPTIONS = [
    "Living my best life! ✨",
    "Good vibes only 🌟",
    "Coffee first, questions later ☕",
    "Chasing dreams and sunsets 🌅",
    "Weekend vibes 🎉",
    "Just another day in paradise 🏝️",
    "Smile more, worry less 😊",
    "Creating memories 📸",
    "Adventure awaits! 🗺️",
    "Stay positive! 💪",
    "Food is my love language 🍕",
    "Work hard, play hard 🎮",
    "Nature therapy 🌿",
    "City lights 🌃",
    "Beach days are the best 🏖️"
]


def generate_demo_email(username, index):
    return f"demo_{username}_{index}@test.local"


def generate_demo_password():
    return "DemoPass123!"


def get_demo_profile_picture(gender):
    pics = [
        "https://i.pravatar.cc/150?img=" + str(random.randint(1, 70))
        for _ in range(10)
    ]
    return random.choice(pics)


# ---------- STATS ----------
@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get data studio stats."""
    total_users = db.query(User).count()
    total_posts = db.query(Post).filter(Post.is_deleted == False).count()
    total_reels = db.query(Reel).filter(Reel.is_deleted == False).count()
    total_followers = db.query(Follower).count()
    total_images = db.query(PostImage).filter(PostImage.is_video == False).count()
    total_videos = db.query(PostImage).filter(PostImage.is_video == True).count() + total_reels

    demo_batches = db.query(DemoDataBatch).filter(DemoDataBatch.is_deleted == False).all()
    demo_users = sum(b.users_count for b in demo_batches)
    demo_posts = sum(b.posts_count for b in demo_batches)
    demo_reels = sum(b.reels_count for b in demo_batches)
    demo_follows = sum(b.follow_edges_count for b in demo_batches)

    return {
        "total_users": total_users,
        "total_posts": total_posts,
        "total_reels": total_reels,
        "total_follow_relations": total_followers,
        "total_photos": total_images,
        "total_videos": total_videos,
        "demo_users": demo_users,
        "demo_posts": demo_posts,
        "demo_reels": demo_reels,
        "demo_follow_edges": demo_follows,
        "demo_batches_count": len(demo_batches)
    }


# ---------- USERS WITH PAGINATION ----------
@router.get("/users")
async def get_users(
    page: int = 1,
    limit: int = 20,
    search: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get users with pagination."""
    query = db.query(User)

    if search:
        query = query.filter(
            (User.username.contains(search)) | (User.full_name.contains(search))
        )

    total = query.count()
    offset = (page - 1) * limit
    users = query.offset(offset).limit(limit).all()

    user_list = []
    for u in users:
        user_list.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "is_verified": u.is_verified,
            "followers_count": u.followers_count,
            "following_count": u.following_count,
            "posts_count": u.posts_count,
            "created_at": u.created_at.isoformat() if u.created_at else None
        })

    return {
        "users": user_list,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }


# ---------- FOLLOW GRAPH ----------
@router.get("/follow-graph")
async def get_follow_graph(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get follow graph data."""
    follows = db.query(Follower).limit(limit).all()
    edges = []
    nodes = set()
    for f in follows:
        edges.append({
            "source": f.follower_id,
            "target": f.following_id
        })
        nodes.add(f.follower_id)
        nodes.add(f.following_id)

    return {
        "nodes": list(nodes),
        "edges": edges
    }


# ---------- SEED 10K DATA ----------
@router.post("/seed-10k")
async def seed_10k_data(
    users_count: int = Form(10000),
    posts_per_user: int = Form(3),
    reels_count: int = Form(2000),
    follow_edges_count: int = Form(15000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate 10K demo data."""
    if users_count > 50000:
        raise HTTPException(400, "Maximum 50,000 users allowed per batch")

    batch_id = str(uuid.uuid4())
    batch = DemoDataBatch(
        id=batch_id,
        batch_name=f"Demo Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        users_count=users_count,
        posts_count=0,
        reels_count=reels_count,
        follow_edges_count=follow_edges_count
    )
    db.add(batch)
    db.commit()

    users_created = 0
    chunk_size = 500
    demo_users = []
    demo_password_hash = hash_password(generate_demo_password())

    for i in range(users_count):
        username_base = random.choice(DEMO_USERNAMES)
        username = f"{username_base}_{i}"
        first_name = random.choice(DEMO_FIRST_NAMES)
        last_name = random.choice(DEMO_LAST_NAMES)
        email = generate_demo_email(username_base, i)

        user = User(
            email=email,
            username=username,
            hashed_password=demo_password_hash,
            full_name=f"{first_name} {last_name}",
            role="user",
            is_verified=random.random() > 0.7,
            badge=random.choice(["new", "popular", "verified", None])
        )
        demo_users.append(user)
        users_created += 1

        if len(demo_users) >= chunk_size:
            db.bulk_save_objects(demo_users)
            db.commit()
            demo_users = []

    if demo_users:
        db.bulk_save_objects(demo_users)
        db.commit()

    all_users = db.query(User).filter(User.email.contains("@test.local")).all()
    if not all_users:
        raise HTTPException(500, "Failed to create demo users")

    user_ids = [u.id for u in all_users]

    # Generate posts
    posts_created = 0
    posts = []
    for user_id in user_ids:
        num_posts = random.randint(1, max(1, posts_per_user))
        for _ in range(num_posts):
            post = Post(
                user_id=user_id,
                content=random.choice(DEMO_CAPTIONS),
                hashtags=[f"#demo", f"#test", f"#socialhub"],
                is_published=True,
                is_deleted=False,
                post_type="normal"
            )
            posts.append(post)
            posts_created += 1

            if len(posts) >= chunk_size:
                db.bulk_save_objects(posts)
                db.commit()
                posts = []

    if posts:
        db.bulk_save_objects(posts)
        db.commit()

    # Generate follow edges
    follows_created = 0
    follows = []
    for _ in range(follow_edges_count):
        source = random.choice(user_ids)
        target = random.choice(user_ids)
        if source != target:
            follows.append(Follower(
                follower_id=source,
                following_id=target,
                is_pending=random.random() > 0.8
            ))
            follows_created += 1

            if len(follows) >= chunk_size:
                db.bulk_save_objects(follows)
                db.commit()
                follows = []

    if follows:
        db.bulk_save_objects(follows)
        db.commit()

    # Generate reels
    reels_created = 0
    reels = []
    demo_reel_videos = [
        "https://storage.example.com/demo/reel1.mp4",
        "https://storage.example.com/demo/reel2.mp4",
        "https://storage.example.com/demo/reel3.mp4"
    ]
    for _ in range(reels_count):
        user_id = random.choice(user_ids)
        reel = Reel(
            user_id=user_id,
            video_url=random.choice(demo_reel_videos),
            caption=random.choice(DEMO_CAPTIONS),
            hashtags=[f"#reel", f"#demo", f"#viral"],
            views_count=random.randint(0, 50000),
            shares_count=random.randint(0, 5000),
            is_deleted=False,
            is_demo=True
        )
        reels.append(reel)
        reels_created += 1

        if len(reels) >= chunk_size:
            db.bulk_save_objects(reels)
            db.commit()
            reels = []

    if reels:
        db.bulk_save_objects(reels)
        db.commit()

    batch.posts_count = posts_created
    batch.reels_count = reels_created
    batch.follow_edges_count = follows_created
    db.commit()
    db.refresh(batch)

    return {
        "success": True,
        "batch_id": batch_id,
        "message": f"Generated {users_created} users, {posts_created} posts, {reels_created} reels, {follows_created} follow edges",
        "users_created": users_created,
        "posts_created": posts_created,
        "reels_created": reels_created,
        "follow_edges_created": follows_created
    }


# ---------- DELETE DEMO BATCH ----------
@router.delete("/demo-batch/{batch_id}")
async def delete_demo_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific demo data batch."""
    batch = db.query(DemoDataBatch).filter(DemoDataBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")

    if batch.is_deleted:
        raise HTTPException(400, "Batch already deleted")

    batch.is_deleted = True
    batch.deleted_at = datetime.utcnow()
    db.commit()
    db.refresh(batch)

    return {
        "success": True,
        "message": f"Batch '{batch.batch_name}' marked as deleted",
        "batch_id": batch_id
    }


# ---------- UPLOAD ORIGINAL MEDIA ----------
@router.post("/media/original/upload")
async def upload_original_media(
    file: UploadFile = File(...),
    ownership_confirmed: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload original photo/video."""
    if not ownership_confirmed:
        raise HTTPException(400, "You must confirm ownership of this media")

    file_ext = os.path.splitext(file.filename)[1].lower()
    file_size = 0

    content = await file.read()
    file_size = len(content)

    is_image = file_ext in ALLOWED_IMAGE_EXTENSIONS
    is_video = file_ext in ALLOWED_VIDEO_EXTENSIONS

    if not is_image and not is_video:
        raise HTTPException(400, f"Unsupported file type. Allowed: images ({', '.join(ALLOWED_IMAGE_EXTENSIONS)}), videos ({', '.join(ALLOWED_VIDEO_EXTENSIONS)})")

    if is_image and file_size > MAX_IMAGE_SIZE:
        raise HTTPException(400, f"Image too large. Max size: {MAX_IMAGE_SIZE // (1024*1024)}MB")

    if is_video and file_size > MAX_VIDEO_SIZE:
        raise HTTPException(400, f"Video too large. Max size: {MAX_VIDEO_SIZE // (1024*1024)}MB")

    user_dir = os.path.join(DEMO_MEDIA_DIR, current_user.id)
    os.makedirs(user_dir, exist_ok=True)

    safe_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(user_dir, safe_filename)
    relative_path = f"original_media/{current_user.id}/{safe_filename}"

    with open(file_path, "wb") as f:
        f.write(content)

    mime_type = file.content_type or ("image/jpeg" if is_image else "video/mp4")
    media_type = "image" if is_image else "video"

    asset = OriginalMediaAsset(
        user_id=current_user.id,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=relative_path,
        file_size=file_size,
        mime_type=mime_type,
        media_type=media_type,
        ownership_confirmed=ownership_confirmed
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # Log the upload
    log = MediaImportLog(
        user_id=current_user.id,
        asset_id=asset.id,
        action="upload",
        source="upload",
        status="success",
        extra_metadata={"filename": file.filename, "size": file_size, "type": media_type}
    )
    db.add(log)
    db.commit()

    return {
        "success": True,
        "asset_id": asset.id,
        "filename": asset.filename,
        "original_filename": asset.original_filename,
        "media_type": asset.media_type,
        "file_size": asset.file_size
    }


# ---------- GET ORIGINAL MEDIA ----------
@router.get("/media/original")
async def get_original_media(
    page: int = 1,
    limit: int = 20,
    media_type: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's original media assets."""
    query = db.query(OriginalMediaAsset).filter(OriginalMediaAsset.user_id == current_user.id)

    if media_type:
        query = query.filter(OriginalMediaAsset.media_type == media_type)

    total = query.count()
    offset = (page - 1) * limit
    assets = query.order_by(OriginalMediaAsset.created_at.desc()).offset(offset).limit(limit).all()

    asset_list = []
    for a in assets:
        asset_list.append({
            "id": a.id,
            "filename": a.filename,
            "url": f"original_media/{current_user.id}/{a.filename}",
            "original_filename": a.original_filename,
            "media_type": a.media_type,
            "file_size": a.file_size,
            "is_used_in_post": a.is_used_in_post,
            "is_used_in_reel": a.is_used_in_reel,
            "ownership_confirmed": a.ownership_confirmed,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })

    return {
        "assets": asset_list,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }


# ---------- CREATE POST FROM ASSET ----------
@router.post("/media/original/{asset_id}/create-post")
async def create_post_from_asset(
    asset_id: str,
    caption: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a post from an uploaded original media asset."""
    asset = db.query(OriginalMediaAsset).filter(
        OriginalMediaAsset.id == asset_id,
        OriginalMediaAsset.user_id == current_user.id
    ).first()
    if not asset:
        raise HTTPException(404, "Asset not found")

    media_url = f"original_media/{current_user.id}/{asset.filename}"

    post = Post(
        user_id=current_user.id,
        content=caption,
        is_published=True,
        is_deleted=False,
        post_type="normal"
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    post_image = PostImage(
        post_id=post.id,
        image_url=media_url,
        is_video=(asset.media_type == "video"),
        video_url=media_url if asset.media_type == "video" else None,
        order=0
    )
    db.add(post_image)

    asset.is_used_in_post = True
    db.commit()
    db.refresh(asset)

    log = MediaImportLog(
        user_id=current_user.id,
        asset_id=asset.id,
        action="create_post",
        source="upload",
        status="success",
        extra_metadata={"post_id": post.id}
    )
    db.add(log)
    db.commit()

    return {
        "success": True,
        "post_id": post.id,
        "message": "Post created successfully"
    }


# ---------- CREATE REEL FROM ASSET ----------
@router.post("/media/original/{asset_id}/create-reel")
async def create_reel_from_asset(
    asset_id: str,
    caption: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a reel from an uploaded original media asset."""
    asset = db.query(OriginalMediaAsset).filter(
        OriginalMediaAsset.id == asset_id,
        OriginalMediaAsset.user_id == current_user.id
    ).first()
    if not asset:
        raise HTTPException(404, "Asset not found")

    if asset.media_type != "video":
        raise HTTPException(400, "Reels require video files")

    video_url = f"original_media/{current_user.id}/{asset.filename}"

    reel = Reel(
        user_id=current_user.id,
        video_url=video_url,
        caption=caption,
        views_count=0,
        shares_count=0,
        is_deleted=False,
        is_demo=False
    )
    db.add(reel)
    db.commit()
    db.refresh(reel)

    asset.is_used_in_reel = True
    db.commit()
    db.refresh(asset)

    log = MediaImportLog(
        user_id=current_user.id,
        asset_id=asset.id,
        action="create_reel",
        source="upload",
        status="success",
        extra_metadata={"reel_id": reel.id}
    )
    db.add(log)
    db.commit()

    return {
        "success": True,
        "reel_id": reel.id,
        "message": "Reel created successfully"
    }


# ---------- ANALYTICS ----------
@router.get("/media/original/analytics")
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics for original media."""
    total_images = db.query(OriginalMediaAsset).filter(
        OriginalMediaAsset.user_id == current_user.id,
        OriginalMediaAsset.media_type == "image"
    ).count()

    total_videos = db.query(OriginalMediaAsset).filter(
        OriginalMediaAsset.user_id == current_user.id,
        OriginalMediaAsset.media_type == "video"
    ).count()

    used_in_posts = db.query(OriginalMediaAsset).filter(
        OriginalMediaAsset.user_id == current_user.id,
        OriginalMediaAsset.is_used_in_post == True
    ).count()

    used_in_reels = db.query(OriginalMediaAsset).filter(
        OriginalMediaAsset.user_id == current_user.id,
        OriginalMediaAsset.is_used_in_reel == True
    ).count()

    recent_logs = db.query(MediaImportLog).filter(
        MediaImportLog.user_id == current_user.id
    ).order_by(MediaImportLog.created_at.desc()).limit(20).all()

    logs = []
    for log in recent_logs:
        logs.append({
            "id": log.id,
            "action": log.action,
            "source": log.source,
            "status": log.status,
            "created_at": log.created_at.isoformat() if log.created_at else None
        })

    return {
        "total_assets": total_images + total_videos,
        "total_images": total_images,
        "total_videos": total_videos,
        "used_in_posts": used_in_posts,
        "used_in_reels": used_in_reels,
        "recent_logs": logs
    }