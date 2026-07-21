"""Story Highlights - Feature 3"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.models import User, Story, StoryHighlight
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/api/highlights", tags=["Story Highlights"])


class CreateHighlightRequest(BaseModel):
    story_id: str
    title: str = Field(..., max_length=100)
    cover_url: Optional[str] = None


@router.get("/user/{user_id}")
def get_user_highlights(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get highlights for a user's profile."""
    highlights = db.query(StoryHighlight).filter(
        StoryHighlight.user_id == user_id
    ).order_by(StoryHighlight.created_at.desc()).all()
    
    result = []
    for h in highlights:
        story = db.query(Story).filter(Story.id == h.story_id).first()
        result.append({
            "id": h.id,
            "title": h.title,
            "cover_url": h.cover_url or (story.media_url if story else None),
            "story_id": h.story_id,
            "media_url": story.media_url if story else None,
            "created_at": str(h.created_at),
        })
    return {"highlights": result}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_highlight(
    request: CreateHighlightRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a story to highlights."""
    story = db.query(Story).filter(
        Story.id == request.story_id,
        Story.user_id == current_user.id
    ).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    existing = db.query(StoryHighlight).filter(
        StoryHighlight.story_id == request.story_id,
        StoryHighlight.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Story already in highlights")
    
    highlight = StoryHighlight(
        user_id=current_user.id,
        story_id=request.story_id,
        title=request.title,
        cover_url=request.cover_url or story.media_url,
    )
    db.add(highlight)
    db.commit()
    db.refresh(highlight)
    return {"id": highlight.id, "title": highlight.title, "message": "Story added to highlights"}


@router.delete("/{highlight_id}")
def delete_highlight(
    highlight_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a highlight."""
    highlight = db.query(StoryHighlight).filter(
        StoryHighlight.id == highlight_id,
        StoryHighlight.user_id == current_user.id
    ).first()
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")
    
    db.delete(highlight)
    db.commit()
    return {"message": "Highlight removed"}