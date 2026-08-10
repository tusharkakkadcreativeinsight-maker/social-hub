from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from typing import List

from ..database import get_db
from ..models.models import User, Story, StoryReaction, StoryView, StoryHighlight, Follower, StoryPoll
from ..models.models import Notification
from ..schemas.schemas import (
    StoryResponse, StoryReactionRequest, StoryHighlightCreate,
    StoryHighlightResponse, StoryViewerResponse, UserSearchResult
)
from ..utils.dependencies import get_current_user, save_upload_file, validate_image_file, validate_video_file
from ..config import settings
from ..utils.time import expires_after, utcnow_naive

router = APIRouter(prefix="/api/stories", tags=["Stories"])


def _story_response(story: Story, db: Session):
    viewers_count = db.query(StoryView).filter(StoryView.story_id == story.id).count()
    response = StoryResponse(
        id=story.id, user_id=story.user_id, media_url=story.media_url,
        media_type=story.media_type, caption=story.caption,
        expires_at=story.expires_at, created_at=story.created_at,
        user=story.user, is_expired=story.is_expired, viewers_count=viewers_count
    ).model_dump()
    response["polls"] = [
        {
            "id": poll.id,
            "poll_type": poll.poll_type,
            "question": poll.question,
            "options": poll.options or [],
            "total_votes": len(poll.votes),
            "results": {option: sum(1 for vote in poll.votes if vote.answer == option) for option in (poll.options or [])},
        }
        for poll in db.query(StoryPoll).filter(StoryPoll.story_id == story.id).all()
    ]
    first_highlight = story.highlights[0] if getattr(story, "highlights", None) else None
    response["highlight"] = {"id": first_highlight.id, "title": first_highlight.title, "cover_url": first_highlight.cover_url} if first_highlight else None
    return response


@router.post("", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    caption: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new story (expires in 24 hours)."""
    media_type = "image"
    if validate_video_file(file):
        media_type = "video"
    elif not validate_image_file(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid story media. Upload JPG, PNG, GIF, WEBP, MP4, WEBM, MOV, or AVI."
        )
    try:
        file_path = await save_upload_file(settings.UPLOAD_DIR, file, "stories")
        story = Story(
            user_id=current_user.id, media_url=file_path, media_type=media_type,
            caption=(caption or None),
            expires_at=expires_after(settings.STORY_DURATION_HOURS)
        )
        db.add(story)
        db.commit()
        db.refresh(story)
        return _story_response(story, db)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save story in database") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not upload story media") from exc


@router.get("", response_model=List[dict])
def get_stories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active stories from followed users."""
    followed_ids = db.query(Follower.following_id).filter(
        Follower.follower_id == current_user.id, Follower.is_pending == False
    ).all()
    followed_ids = [f[0] for f in followed_ids]
    followed_ids.append(current_user.id)

    stories = db.query(Story).filter(
        Story.user_id.in_(followed_ids), Story.is_deleted == False,
        Story.expires_at > utcnow_naive()
    ).order_by(Story.created_at.desc()).all()

    result = []
    for story in stories:
        result.append(_story_response(story, db))
    return result


@router.get("/user/{user_id}", response_model=List[dict])
def get_user_stories(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active stories for a specific user."""
    stories = db.query(Story).filter(
        Story.user_id == user_id, Story.is_deleted == False,
        Story.expires_at > utcnow_naive()
    ).order_by(Story.created_at.desc()).all()
    result = []
    for story in stories:
        result.append(_story_response(story, db))
    return result


@router.get("/highlights/{user_id}", response_model=List[StoryHighlightResponse])
def get_highlights(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get story highlights for a user."""
    highlights = db.query(StoryHighlight).filter(
        StoryHighlight.user_id == user_id
    ).order_by(StoryHighlight.created_at.desc()).all()
    return highlights


@router.delete("/highlights/{highlight_id}")
def remove_highlight(
    highlight_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a story highlight."""
    highlight = db.query(StoryHighlight).filter(
        StoryHighlight.id == highlight_id, StoryHighlight.user_id == current_user.id
    ).first()
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")
    db.delete(highlight)
    db.commit()
    return {"message": "Highlight removed"}


@router.get("/archive", response_model=List[dict])
def get_archived_stories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get archived stories for current user. Must stay above /{story_id}."""
    stories = db.query(Story).filter(
        Story.user_id == current_user.id, Story.is_deleted == False
    ).order_by(Story.created_at.desc()).all()
    result = []
    for story in stories:
        result.append(_story_response(story, db))
    return result


@router.post("/{story_id}/view")
def view_story(
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a story as viewed."""
    story = db.query(Story).filter(Story.id == story_id, Story.is_deleted == False).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    existing = db.query(StoryView).filter(
        StoryView.story_id == story_id, StoryView.user_id == current_user.id
    ).first()

    if not existing:
        view = StoryView(story_id=story_id, user_id=current_user.id)
        db.add(view)
        db.commit()

    return {"message": "Story viewed"}


@router.get("/{story_id}/viewers", response_model=List[StoryViewerResponse])
def get_story_viewers(
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get viewers of a story."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only story owner can see viewers")

    views = db.query(StoryView).filter(StoryView.story_id == story_id).order_by(StoryView.viewed_at.desc()).all()
    result = []
    for view in views:
        user = db.query(User).filter(User.id == view.user_id).first()
        if user:
            pp = user.profile_picture if hasattr(user, 'profile_picture') else None
            result.append(StoryViewerResponse(
                user=UserSearchResult(
                    id=user.id, username=user.username, full_name=user.full_name,
                    profile_picture=pp, is_verified=user.is_verified,
                    followers_count=user.followers_count, badge=getattr(user, 'badge', None)
                ),
                viewed_at=view.viewed_at
            ))
    return result


@router.post("/{story_id}/react")
def react_to_story(
    story_id: str,
    request: StoryReactionRequest = StoryReactionRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """React to a story."""
    story = db.query(Story).filter(Story.id == story_id, Story.is_deleted == False).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    existing = db.query(StoryReaction).filter(
        StoryReaction.story_id == story_id, StoryReaction.user_id == current_user.id
    ).first()

    if existing:
        existing.reaction = request.reaction
    else:
        reaction = StoryReaction(story_id=story_id, user_id=current_user.id, reaction=request.reaction)
        db.add(reaction)
    if story.user_id != current_user.id:
        db.add(Notification(
            user_id=story.user_id, actor_id=current_user.id, type="story_reaction",
            message=f"{current_user.username} reacted to your story", reference_id=story_id,
            reference_type="story"
        ))

    db.commit()
    return {"message": "Reaction added"}


@router.post("/{story_id}/highlight", response_model=StoryHighlightResponse, status_code=status.HTTP_201_CREATED)
def add_to_highlights(
    story_id: str,
    request: StoryHighlightCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a story to highlights."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only highlight your own stories")

    highlight = StoryHighlight(
        user_id=current_user.id, story_id=story_id,
        title=request.title, cover_url=request.cover_url
    )
    db.add(highlight)
    db.commit()
    db.refresh(highlight)
    return highlight


@router.delete("/{story_id}")
def delete_story(
    story_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a story."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can delete only your own story")
    story.is_deleted = True
    story.deleted_at = utcnow_naive()
    db.commit()
    return {"message": "Story deleted successfully"}