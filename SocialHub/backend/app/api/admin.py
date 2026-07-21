from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta
from typing import List, Optional

from ..database import get_db
from ..models.models import (
    User, Post, Report, Profile, Story, Reel, AuditLog, Warning,
    Like, Comment, Notification, Follower, ReelLike, ReelComment
)
from ..schemas.schemas import (
    AdminDashboard, UserResponse, BanUserRequest,
    ReportResponse, UpdateReportStatus, UserProfileResponse,
    PostResponse, PostImageResponse, UserSearchResult,
    WarningCreateRequest, WarningResponse, AuditLogResponse
)
from ..utils.dependencies import get_admin_user
from ..utils.time import utcnow_naive

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _user_search_dict(user: User | None):
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "profile_picture": user.profile_picture if hasattr(user, "profile_picture") else None,
        "is_verified": user.is_verified,
        "followers_count": user.followers_count if hasattr(user, "followers_count") else 0,
        "badge": getattr(user, "badge", None),
    }


def _post_summary(post: Post):
    return {
        "id": post.id,
        "user_id": post.user_id,
        "content": post.content,
        "is_published": post.is_published,
        "is_deleted": post.is_deleted,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "likes_count": post.likes_count,
        "comments_count": post.comments_count,
        "author": _user_search_dict(post.author),
        "images": [
            {"id": img.id, "image_url": img.image_url, "video_url": img.video_url, "is_video": img.is_video, "order": img.order}
            for img in (post.images or [])
        ],
    }


def log_admin_action(db, admin_id, action, target_type=None, target_id=None, details=None):
    """Create an audit log entry."""
    log = AuditLog(
        admin_id=admin_id, action=action,
        target_type=target_type, target_id=target_id, details=details
    )
    db.add(log)


@router.get("/dashboard", response_model=AdminDashboard)
def get_dashboard(
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get admin dashboard statistics."""
    today = utcnow_naive().replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = db.query(User).count()
    total_posts = db.query(Post).filter(Post.is_deleted == False).count()
    total_reports = db.query(Report).count()
    active_users_today = db.query(User).filter(User.last_login >= today).count()
    new_users_today = db.query(User).filter(User.created_at >= today).count()
    total_stories = db.query(Story).filter(Story.is_deleted == False).count()
    total_reels = db.query(Reel).filter(Reel.is_deleted == False).count()

    return AdminDashboard(
        total_users=total_users, total_posts=total_posts, total_reports=total_reports,
        active_users_today=active_users_today, new_users_today=new_users_today,
        total_stories=total_stories, total_reels=total_reels
    )


@router.get("/reports")
def get_reports(
    status_filter: Optional[str] = None,
    page: int = 1, page_size: int = 20,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get all reports (admin)."""
    offset = (page - 1) * page_size
    query = db.query(Report)

    if status_filter:
        query = query.filter(Report.status == status_filter)

    total = query.count()
    reports = query.order_by(Report.created_at.desc()).offset(offset).limit(page_size).all()

    report_responses = []
    for report in reports:
        reporter_data = _user_search_dict(report.reporter)
        reported_data = _user_search_dict(report.reported_user)
        report_responses.append({
            "id": report.id, "reported_by": report.reported_by,
            "reported_user_id": report.reported_user_id, "post_id": report.post_id,
            "comment_id": report.comment_id, "reel_id": report.reel_id, "story_id": report.story_id,
            "reason": report.reason,
            "description": report.description, "status": report.status,
            "created_at": report.created_at, "reporter": reporter_data,
            "reported_user": reported_data,
        })

    return {"reports": report_responses, "total": total, "page": page, "page_size": page_size, "has_next": offset + page_size < total}


@router.post("/reports/{report_id}/resolve")
def resolve_report(
    report_id: str,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Resolve a report (admin)."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = "resolved"
    report.resolved_by = current_user.id
    report.resolved_at = utcnow_naive()

    log_admin_action(db, current_user.id, "resolved report", "report", report_id)
    db.commit()
    return {"message": "Report resolved"}


@router.post("/reports/{report_id}/dismiss")
def dismiss_report(
    report_id: str,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Dismiss a report (admin)."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = "dismissed"
    report.resolved_by = current_user.id
    report.resolved_at = utcnow_naive()

    log_admin_action(db, current_user.id, "dismissed report", "report", report_id)
    db.commit()
    return {"message": "Report dismissed"}


@router.get("/users")
def get_all_users(
    page: int = 1, page_size: int = 20, search: Optional[str] = None,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get all users (admin)."""
    offset = (page - 1) * page_size
    query = db.query(User)

    if search:
        query = query.filter(
            User.username.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%") |
            User.full_name.ilike(f"%{search}%")
        )

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    user_responses = []
    for user in users:
        pp = user.profile_picture if hasattr(user, 'profile_picture') else None
        user_responses.append({
            "id": user.id, "username": user.username, "full_name": user.full_name,
            "profile_picture": pp, "is_verified": user.is_verified,
            "is_banned": user.is_banned, "role": user.role,
            "followers_count": user.followers_count, "badge": getattr(user, 'badge', None),
            "created_at": user.created_at, "email": user.email,
        })

    return {"users": user_responses, "total": total, "page": page, "page_size": page_size, "has_next": offset + page_size < total}


@router.get("/posts")
def get_all_posts(
    page: int = 1,
    page_size: int = 20,
    include_deleted: bool = False,
    search: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Get posts for admin moderation without exposing secrets."""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size
    query = db.query(Post)
    if not include_deleted:
        query = query.filter(Post.is_deleted == False)
    if search:
        query = query.filter(Post.content.ilike(f"%{search}%"))
    total = query.count()
    posts = query.order_by(Post.created_at.desc()).offset(offset).limit(page_size).all()
    return {
        "posts": [_post_summary(post) for post in posts],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + page_size < total,
    }


@router.post("/users/{user_id}/ban")
def ban_user(
    user_id: str, reason: Optional[str] = None,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Ban a user (admin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role in ["admin"]:
        raise HTTPException(status_code=400, detail="Cannot ban admin users")

    user.is_banned = True
    log_admin_action(db, current_user.id, f"banned user {user.username}", "user", user_id, reason)
    db.commit()
    return {"message": "User banned"}


@router.post("/users/{user_id}/unban")
def unban_user(
    user_id: str,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Unban a user (admin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_banned = False
    log_admin_action(db, current_user.id, f"unbanned user {user.username}", "user", user_id)
    db.commit()
    return {"message": "User unbanned"}


@router.post("/users/{user_id}/warning")
def issue_warning(
    user_id: str,
    warning_type: str = "content_violation",
    reason: str = "",
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Issue a warning to a user (admin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    warning = Warning(
        user_id=user_id,
        issued_by=current_user.id,
        warning_type=warning_type,
        reason=reason or "No reason provided",
    )
    db.add(warning)

    notification = Notification(
        user_id=user_id,
        actor_id=current_user.id,
        type="follow",
        message=f"You received a warning: {reason or warning_type}",
        reference_id=warning.id,
        reference_type="warning",
    )
    db.add(notification)

    log_admin_action(db, current_user.id, f"issued warning to {user.username}", "user", user_id, reason or warning_type)
    db.commit()
    db.refresh(warning)
    return {"message": "Warning issued", "warning": {"id": warning.id, "warning_type": warning.warning_type, "reason": warning.reason, "created_at": warning.created_at}}


@router.get("/warnings")
def get_warnings(
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get all warnings (admin)."""
    warnings = db.query(Warning).order_by(Warning.created_at.desc()).limit(100).all()
    return [
        {
            "id": w.id, "user_id": w.user_id, "issued_by": w.issued_by,
            "warning_type": w.warning_type, "reason": w.reason,
            "is_read": w.is_read, "created_at": w.created_at,
        }
        for w in warnings
    ]


@router.get("/audit-logs")
def get_audit_logs(
    page: int = 1, page_size: int = 50,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get audit logs (admin)."""
    offset = (page - 1) * page_size
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size).all()
    return [
        {
            "id": l.id, "admin_id": l.admin_id, "action": l.action,
            "target_type": l.target_type, "target_id": l.target_id,
            "details": l.details, "created_at": l.created_at,
        }
        for l in logs
    ]


@router.get("/analytics")
def get_analytics(
    days: int = 7, current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get analytics data (admin)."""
    today = utcnow_naive().replace(hour=0, minute=0, second=0, microsecond=0)
    data = []

    for i in range(days - 1, -1, -1):
        day_start = today - timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        users_count = db.query(User).filter(User.created_at >= day_start, User.created_at < day_end).count()
        posts_count = db.query(Post).filter(Post.created_at >= day_start, Post.created_at < day_end, Post.is_deleted == False).count()
        likes_count = db.query(Like).filter(Like.created_at >= day_start, Like.created_at < day_end).count()
        comments_count = db.query(Comment).filter(Comment.created_at >= day_start, Comment.created_at < day_end).count()

        data.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "users_count": users_count, "posts_count": posts_count,
            "likes_count": likes_count, "comments_count": comments_count
        })

    return data