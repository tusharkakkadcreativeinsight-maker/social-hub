from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List

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

router = APIRouter(prefix="/api/admin", tags=["Admin"])


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
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

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


@router.get("/creator-dashboard")
def get_all_creator_dashboard(
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get creator dashboard statistics aggregated for all users (admin)."""
    total_posts = db.query(Post).filter(Post.is_deleted == False).count()
    total_reels = db.query(Reel).filter(Reel.is_deleted == False).count()
    likes = db.query(Like).count()
    comments = db.query(Comment).filter(Comment.is_deleted == False).count()
    reel_likes = db.query(ReelLike).count()
    reel_comments = db.query(ReelComment).filter(ReelComment.is_deleted == False).count()
    views = db.query(func.coalesce(func.sum(Reel.views_count), 0)).filter(Reel.is_deleted == False).scalar() or 0
    followers = db.query(Follower).filter(Follower.is_pending == False).count()
    following = followers
    total_engagements = likes + comments + reel_likes + reel_comments
    engagement = round((total_engagements / max(followers, 1)) * 100, 2)

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
    }


@router.get("/users", response_model=dict)
def get_all_users(
    page: int = 1, page_size: int = 20, search: str = None,
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
        user_responses.append(UserSearchResult(
            id=user.id, username=user.username, full_name=user.full_name,
            profile_picture=pp, is_verified=user.is_verified,
            followers_count=user.followers_count, badge=getattr(user, 'badge', None)
        ))

    return {"users": user_responses, "total": total, "page": page, "page_size": page_size, "has_next": offset + page_size < total}


@router.get("/reports", response_model=dict)
def get_reports(
    status_filter: str = None, page: int = 1, page_size: int = 20,
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
        reporter_data = None
        if report.reporter:
            pp = report.reporter.profile_picture if hasattr(report.reporter, 'profile_picture') else None
            reporter_data = UserSearchResult(
                id=report.reporter.id, username=report.reporter.username,
                full_name=report.reporter.full_name, profile_picture=pp,
                is_verified=report.reporter.is_verified, followers_count=report.reporter.followers_count
            )
        reported_data = None
        if report.reported_user:
            pp = report.reported_user.profile_picture if hasattr(report.reported_user, 'profile_picture') else None
            reported_data = UserSearchResult(
                id=report.reported_user.id, username=report.reported_user.username,
                full_name=report.reported_user.full_name, profile_picture=pp,
                is_verified=report.reported_user.is_verified, followers_count=report.reported_user.followers_count
            )

        report_responses.append(ReportResponse(
            id=report.id, reported_by=report.reported_by,
            reported_user_id=report.reported_user_id, post_id=report.post_id,
            comment_id=report.comment_id, reason=report.reason,
            description=report.description, status=report.status,
            created_at=report.created_at, reporter=reporter_data, reported_user=reported_data
        ).model_dump())

    return {"reports": report_responses, "total": total, "page": page, "page_size": page_size, "has_next": offset + page_size < total}


@router.get("/posts", response_model=dict)
def get_all_posts(
    page: int = 1, page_size: int = 20,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get all posts (admin)."""
    offset = (page - 1) * page_size
    query = db.query(Post).filter(Post.is_deleted == False)
    total = query.count()
    posts = query.order_by(Post.created_at.desc()).offset(offset).limit(page_size).all()

    post_responses = []
    for post in posts:
        author_data = None
        if post.author:
            pp = post.author.profile_picture if hasattr(post.author, 'profile_picture') else None
            author_data = UserSearchResult(
                id=post.author.id, username=post.author.username,
                full_name=post.author.full_name, profile_picture=pp,
                is_verified=post.author.is_verified, followers_count=post.author.followers_count
            )
        images = []
        for img in post.images:
            images.append(PostImageResponse(
                id=img.id, image_url=img.image_url, is_video=img.is_video,
                video_url=img.video_url, order=img.order
            ))
        post_responses.append(PostResponse(
            id=post.id, user_id=post.user_id, content=post.content,
            is_scheduled=post.is_scheduled,
            scheduled_time=post.scheduled_time,
            is_published=post.is_published,
            is_deleted=post.is_deleted,
            hashtags=post.hashtags, post_type=post.post_type,
            repost_id=post.repost_id,
            likes_count=post.likes_count, comments_count=post.comments_count,
            shares_count=getattr(post, 'shares_count', 0),
            created_at=post.created_at, updated_at=post.updated_at,
            images=images, author=author_data
        ).model_dump())

    return {"posts": post_responses, "total": total, "page": page, "page_size": page_size, "has_next": offset + page_size < total}


@router.put("/reports/{report_id}")
def update_report_status(
    report_id: str, request: UpdateReportStatus,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Update report status (admin)."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = request.status
    report.resolved_by = current_user.id
    report.resolved_at = datetime.utcnow()

    log_admin_action(db, current_user.id, f"Updated report status to {request.status}", "report", report_id)
    db.commit()
    return {"message": f"Report {request.status}"}


@router.put("/users/{user_id}/ban")
def ban_user(
    user_id: str, request: BanUserRequest,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Ban or unban a user (admin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role in ["admin"]:
        raise HTTPException(status_code=400, detail="Cannot ban admin users")

    user.is_banned = request.is_banned
    action = "banned" if request.is_banned else "unbanned"
    log_admin_action(db, current_user.id, f"{action} user {user.username}", "user", user_id, request.reason)
    db.commit()
    return {"message": f"User {action} successfully"}


@router.post("/warnings", response_model=WarningResponse, status_code=status.HTTP_201_CREATED)
def issue_warning(
    request: WarningCreateRequest,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Issue a warning to a user."""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    warning = Warning(
        user_id=request.user_id, issued_by=current_user.id,
        warning_type=request.warning_type, reason=request.reason
    )
    db.add(warning)

    notification = Notification(
        user_id=request.user_id, actor_id=current_user.id,
        type="follow", message=f"You received a warning: {request.reason}",
        reference_id=warning.id, reference_type="warning"
    )
    db.add(notification)

    log_admin_action(db, current_user.id, f"Issued warning to {user.username}", "user", request.user_id, request.reason)
    db.commit()
    db.refresh(warning)
    return warning


@router.get("/warnings", response_model=List[WarningResponse])
def get_warnings(
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get all warnings."""
    warnings = db.query(Warning).order_by(Warning.created_at.desc()).limit(100).all()
    return warnings


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    page: int = 1, page_size: int = 50,
    current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get audit logs."""
    offset = (page - 1) * page_size
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size).all()
    return logs


@router.get("/analytics")
def get_analytics(
    days: int = 7, current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)
):
    """Get analytics data (admin)."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
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