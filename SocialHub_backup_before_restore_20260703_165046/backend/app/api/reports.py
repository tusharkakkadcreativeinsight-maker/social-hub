from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.models import User, Report
from ..schemas.schemas import CreateReportRequest, ReportResponse
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    request: CreateReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a report."""
    report = Report(
        reported_by=current_user.id,
        reported_user_id=request.reported_user_id,
        post_id=request.post_id,
        comment_id=request.comment_id,
        reason=request.reason,
        description=request.description
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report