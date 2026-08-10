"""Creator Monetization Demo - Feature 10"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field
from datetime import timedelta

from ..database import get_db
from ..models.models import User, CreatorWallet, EarningRecord, PayoutRequest, Notification, AuditLog
from ..utils.dependencies import get_current_user, get_admin_user
from ..utils.time import utcnow_naive

router = APIRouter(prefix="/api/wallet", tags=["Wallet"])


class PayoutRequestCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: str = Field(default="bank_transfer")
    account_details: Optional[str] = None


@router.get("")
def get_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get creator wallet and earnings."""
    wallet = db.query(CreatorWallet).filter(CreatorWallet.user_id == current_user.id).first()
    if not wallet:
        wallet = CreatorWallet(user_id=current_user.id)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    
    # Demo earnings
    db.query(EarningRecord).filter(EarningRecord.user_id == current_user.id).count()
    
    return {
        "balance": wallet.balance,
        "total_earned": wallet.total_earned,
        "total_withdrawn": wallet.total_withdrawn,
        "created_at": str(wallet.created_at),
    }


@router.get("/earnings")
def get_earnings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get earning history."""
    earnings = db.query(EarningRecord).filter(
        EarningRecord.user_id == current_user.id
    ).order_by(EarningRecord.created_at.desc()).limit(50).all()
    
    return {
        "earnings": [
            {
                "id": e.id, "amount": e.amount,
                "source": e.source, "source_id": e.source_id,
                "description": e.description,
                "created_at": str(e.created_at),
            }
            for e in earnings
        ],
        "total": len(earnings),
    }


@router.get("/payouts")
def get_payouts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payout requests."""
    payouts = db.query(PayoutRequest).filter(
        PayoutRequest.user_id == current_user.id
    ).order_by(PayoutRequest.created_at.desc()).all()
    
    return {
        "payouts": [
            {
                "id": p.id, "amount": p.amount,
                "payment_method": p.payment_method,
                "status": p.status,
                "admin_note": p.admin_note,
                "created_at": str(p.created_at),
                "updated_at": str(p.updated_at),
            }
            for p in payouts
        ]
    }


@router.post("/payouts", status_code=status.HTTP_201_CREATED)
def request_payout(
    request: PayoutRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request a payout."""
    wallet = db.query(CreatorWallet).filter(CreatorWallet.user_id == current_user.id).first()
    if not wallet or wallet.balance < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    payout = PayoutRequest(
        user_id=current_user.id,
        amount=request.amount,
        payment_method=request.payment_method,
        account_details=request.account_details,
    )
    db.add(payout)
    
    wallet.balance -= request.amount
    wallet.total_withdrawn += request.amount
    
    db.commit()
    return {"message": "Payout requested", "payout_id": payout.id, "status": "pending"}


@router.post("/demo/generate-earnings")
def generate_demo_earnings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate demo earnings data."""
    wallet = db.query(CreatorWallet).filter(CreatorWallet.user_id == current_user.id).first()
    if not wallet:
        wallet = CreatorWallet(user_id=current_user.id)
        db.add(wallet)
        db.flush()
    
    demo_data = [
        {"amount": 250.00, "source": "reel", "description": "Reel earnings - Summer Vibes"},
        {"amount": 180.00, "source": "post", "description": "Sponsored post - Tech Review"},
        {"amount": 500.00, "source": "collab", "description": "Brand collaboration - Fashion Week"},
        {"amount": 75.00, "source": "bonus", "description": "Creator bonus - July 2026"},
        {"amount": 320.00, "source": "reel", "description": "Reel earnings - Travel Diary"},
        {"amount": 150.00, "source": "post", "description": "Sponsored post - Fitness Tips"},
        {"amount": 100.00, "source": "tip", "description": "Fan tip - Thank you!"},
        {"amount": 450.00, "source": "collab", "description": "Brand collaboration - Gaming Setup"},
    ]
    
    for data in demo_data:
        earning = EarningRecord(
            user_id=current_user.id,
            amount=data["amount"],
            source=data["source"],
            description=data["description"],
        )
        db.add(earning)
        wallet.balance += data["amount"]
        wallet.total_earned += data["amount"]
    
    db.commit()
    return {"message": "Demo earnings generated", "total_added": 2025.00, "new_balance": wallet.balance}


# Admin endpoints for payout management
@router.get("/admin/payouts")
def admin_get_payouts(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin: Get all payout requests."""
    query = db.query(PayoutRequest)
    if status_filter:
        query = query.filter(PayoutRequest.status == status_filter)
    payouts = query.order_by(PayoutRequest.created_at.desc()).all()
    
    return {
        "payouts": [
            {
                "id": p.id, "user_id": p.user_id,
                "username": p.user.username if p.user else None,
                "amount": p.amount, "payment_method": p.payment_method,
                "status": p.status, "account_details": p.account_details,
                "admin_note": p.admin_note,
                "created_at": str(p.created_at),
            }
            for p in payouts
        ]
    }


@router.post("/admin/payouts/{payout_id}/process")
def admin_process_payout(
    payout_id: str,
    action: str = "approve",
    admin_note: Optional[str] = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin: Approve or reject payout."""
    payout = db.query(PayoutRequest).filter(PayoutRequest.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    
    if action == "approve":
        payout.status = "approved"
        notification_msg = f"Your payout request of ${payout.amount:.2f} has been approved!"
    elif action == "reject":
        payout.status = "rejected"
        # Refund balance
        wallet = db.query(CreatorWallet).filter(CreatorWallet.user_id == payout.user_id).first()
        if wallet:
            wallet.balance += payout.amount
            wallet.total_withdrawn -= payout.amount
        notification_msg = f"Your payout request of ${payout.amount:.2f} was rejected. {admin_note or ''}"
    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    payout.processed_by = current_user.id
    payout.processed_at = utcnow_naive()
    payout.admin_note = admin_note
    
    notification = Notification(
        user_id=payout.user_id,
        actor_id=current_user.id,
        type="follow",
        message=notification_msg,
        reference_id=payout.id,
        reference_type="payout",
    )
    db.add(notification)
    
    log = AuditLog(
        admin_id=current_user.id,
        action=f"{action} payout of ${payout.amount:.2f}",
        target_type="payout",
        target_id=payout.id,
    )
    db.add(log)
    
    db.commit()
    return {"message": f"Payout {action}d"}