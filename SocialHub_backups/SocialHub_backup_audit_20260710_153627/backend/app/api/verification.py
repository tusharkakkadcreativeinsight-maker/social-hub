"""Verified Badge System - Feature 1"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.models import User, VerificationRequest, VerificationStatus, Notification, AuditLog
from ..utils.dependencies import get_current_user, get_admin_user
from ..utils.time import utcnow_naive

router = APIRouter(prefix="/api/verification", tags=["Verification"])


class VerificationRequestCreate(BaseModel):
    full_name: str = Field(..., max_length=150)
    reason: str = Field(..., max_length=1000)
    category: str = Field(default="creator", max_length=50)


class VerificationRequestResponse(BaseModel):
    id: str
    user_id: str
    full_name: str
    reason: str
    document_url: Optional[str] = None
    category: str
    status: str
    admin_note: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class VerificationAdminAction(BaseModel):
    status: str  # 'approved' or 'rejected'
    admin_note: Optional[str] = None


@router.post("/request", status_code=status.HTTP_201_CREATED)
def request_verification(
    request: VerificationRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a verification request."""
    existing = db.query(VerificationRequest).filter(VerificationRequest.user_id == current_user.id).first()
    if existing and existing.status == VerificationStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="You already have a pending verification request")
    
    if existing:
        # Update existing rejected request
        existing.full_name = request.full_name
        existing.reason = request.reason
        existing.category = request.category
        existing.status = VerificationStatus.PENDING.value
        existing.admin_note = None
        existing.reviewed_by = None
        existing.reviewed_at = None
    else:
        vr = VerificationRequest(
            user_id=current_user.id,
            full_name=request.full_name,
            reason=request.reason,
            category=request.category,
        )
        db.add(vr)
    
    db.commit()
    return {"message": "Verification request submitted successfully", "status": "pending"}


@router.get("/status")
def get_verification_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's verification request status."""
    vr = db.query(VerificationRequest).filter(VerificationRequest.user_id == current_user.id).first()
    if not vr:
        return {"has_requested": False, "is_verified": current_user.is_verified}
    return {
        "has_requested": True,
        "id": vr.id,
        "status": vr.status,
        "full_name": vr.full_name,
        "category": vr.category,
        "reason": vr.reason,
        "admin_note": vr.admin_note,
        "created_at": str(vr.created_at),
        "is_verified": current_user.is_verified,
    }


@router.get("/requests")
def get_all_verification_requests(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin: Get all verification requests."""
    query = db.query(VerificationRequest)
    if status_filter:
        query = query.filter(VerificationRequest.status == status_filter)
    requests = query.order_by(VerificationRequest.created_at.desc()).all()
    
    result = []
    for vr in requests:
        user_data = None
        if vr.user:
            user_data = {
                "id": vr.user.id, "username": vr.user.username,
                "full_name": vr.user.full_name, "is_verified": vr.user.is_verified,
                "profile_picture": vr.user.profile_picture,
            }
        result.append({
            "id": vr.id, "user": user_data,
            "full_name": vr.full_name, "reason": vr.reason,
            "category": vr.category, "status": vr.status,
            "admin_note": vr.admin_note, "created_at": str(vr.created_at),
        })
    return {"requests": result, "total": len(result)}


@router.post("/requests/{request_id}/review")
def review_verification_request(
    request_id: str,
    action: VerificationAdminAction,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin: Approve or reject a verification request."""
    vr = db.query(VerificationRequest).filter(VerificationRequest.id == request_id).first()
    if not vr:
        raise HTTPException(status_code=404, detail="Verification request not found")
    
    if action.status not in [VerificationStatus.APPROVED.value, VerificationStatus.REJECTED.value]:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")
    
    vr.status = action.status
    vr.reviewed_by = current_user.id
    vr.reviewed_at = utcnow_naive()
    vr.admin_note = action.admin_note
    
    # Update user verification badge
    user = db.query(User).filter(User.id == vr.user_id).first()
    if user:
        if action.status == VerificationStatus.APPROVED.value:
            user.is_verified = True
            user.badge = "verified"
        else:
            user.is_verified = False
    
    # Create notification for user
    notif_msg = "Your verification request has been approved! 🎉" if action.status == "approved" else f"Your verification request was rejected. Reason: {action.admin_note or 'Not specified'}"
    notification = Notification(
        user_id=vr.user_id,
        actor_id=current_user.id,
        type="follow",
        message=notif_msg,
        reference_id=vr.id,
        reference_type="verification",
    )
    db.add(notification)
    
    # Audit log
    log = AuditLog(
        admin_id=current_user.id,
        action=f"{action.status} verification for {user.username if user else 'unknown'}",
        target_type="verification",
        target_id=vr.id,
        details=action.admin_note,
    )
    db.add(log)
    
    db.commit()
    return {"message": f"Verification request {action.status}", "user_verified": user.is_verified if user else False}