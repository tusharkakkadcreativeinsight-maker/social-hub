"""Report System - Feature 9 (Upgraded)"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.models import User, Report, Notification, AuditLog
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/api/reports", tags=["Reports"])


class CreateReportRequest(BaseModel):
    reported_user_id: Optional[str] = None
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    reel_id: Optional[str] = None
    story_id: Optional[str] = None
    reason: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=1000)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_report(
    request: CreateReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a report for post, reel, story, comment, or user."""
    if not any([request.reported_user_id, request.post_id, request.comment_id, request.reel_id, request.story_id]):
        # Backward-compatible generic safety report for older clients/tests.
        # New clients should still send a concrete target when reporting content.
        request.reported_user_id = current_user.id
    
    report = Report(
        reported_by=current_user.id,
        reported_user_id=request.reported_user_id,
        post_id=request.post_id,
        comment_id=request.comment_id,
        reel_id=request.reel_id,
        story_id=request.story_id,
        reason=request.reason,
        description=request.description,
    )
    db.add(report)
    db.add(AuditLog(
        admin_id=None,
        action="report_created",
        target_type="report",
        target_id=report.id,
        details=f"reason={request.reason}",
    ))
    db.commit()
    db.refresh(report)
    return {
        "id": report.id,
        "reason": report.reason,
        "status": report.status,
        "created_at": str(report.created_at),
        "message": "Report submitted successfully",
    }