from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.models import User, Post, Comment, CommentReaction, Notification
from ..schemas.schemas import CommentCreate, CommentUpdate, CommentResponse, CommentReactionRequest
from ..utils.dependencies import get_current_user
from ..utils.time import utcnow_naive

router = APIRouter(prefix="/api/comments", tags=["Comments"])


@router.post("/{post_id}", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: str,
    request: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a comment on a post."""
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if request.parent_id:
        parent = db.query(Comment).filter(Comment.id == request.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found")

    comment = Comment(
        post_id=post_id, user_id=current_user.id,
        content=request.content, parent_id=request.parent_id
    )
    db.add(comment)
    db.flush()

    if post.user_id != current_user.id:
        notification = Notification(
            user_id=post.user_id, actor_id=current_user.id,
            type="comment", message=f"{current_user.username} commented on your post",
            reference_id=post_id, reference_type="post"
        )
        db.add(notification)

    db.commit()
    db.refresh(comment)

    return CommentResponse(
        id=comment.id, post_id=comment.post_id, user_id=comment.user_id,
        parent_id=comment.parent_id, content=comment.content,
        is_deleted=comment.is_deleted, created_at=comment.created_at,
        updated_at=comment.updated_at,
        author=comment.author, replies=[], reactions_count=0
    )


@router.get("/{post_id}", response_model=List[CommentResponse])
def get_post_comments(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all comments for a post."""
    comments = db.query(Comment).filter(
        Comment.post_id == post_id,
        Comment.parent_id == None,
        Comment.is_deleted == False
    ).order_by(Comment.created_at.asc()).all()

    result = []
    for comment in comments:
        replies = db.query(Comment).filter(
            Comment.parent_id == comment.id,
            Comment.is_deleted == False
        ).order_by(Comment.created_at.asc()).all()

        reactions_count = db.query(CommentReaction).filter(
            CommentReaction.comment_id == comment.id
        ).count()

        reply_responses = []
        for reply in replies:
            reply_reactions_count = db.query(CommentReaction).filter(
                CommentReaction.comment_id == reply.id
            ).count()
            reply_responses.append(CommentResponse(
                id=reply.id, post_id=reply.post_id, user_id=reply.user_id,
                parent_id=reply.parent_id, content=reply.content,
                is_deleted=reply.is_deleted, created_at=reply.created_at,
                updated_at=reply.updated_at, author=reply.author,
                replies=[], reactions_count=reply_reactions_count
            ))

        result.append(CommentResponse(
            id=comment.id, post_id=comment.post_id, user_id=comment.user_id,
            parent_id=comment.parent_id, content=comment.content,
            is_deleted=comment.is_deleted, created_at=comment.created_at,
            updated_at=comment.updated_at, author=comment.author,
            replies=reply_responses, reactions_count=reactions_count
        ))

    return result


@router.put("/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: str,
    request: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a comment."""
    comment = db.query(Comment).filter(
        Comment.id == comment_id, Comment.user_id == current_user.id
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found or not authorized")

    comment.content = request.content
    db.commit()
    db.refresh(comment)

    reactions_count = db.query(CommentReaction).filter(
        CommentReaction.comment_id == comment.id
    ).count()

    return CommentResponse(
        id=comment.id, post_id=comment.post_id, user_id=comment.user_id,
        parent_id=comment.parent_id, content=comment.content,
        is_deleted=comment.is_deleted, created_at=comment.created_at,
        updated_at=comment.updated_at, author=comment.author,
        replies=[], reactions_count=reactions_count
    )


@router.delete("/{comment_id}")
def delete_comment(
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete a comment."""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can delete only your own comment")

    comment.is_deleted = True
    comment.deleted_at = utcnow_naive()
    db.commit()
    return {"message": "Comment deleted successfully"}


@router.post("/{comment_id}/react")
def react_to_comment(
    comment_id: str,
    request: CommentReactionRequest = CommentReactionRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """React to a comment."""
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.is_deleted == False).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    existing = db.query(CommentReaction).filter(
        CommentReaction.comment_id == comment_id,
        CommentReaction.user_id == current_user.id
    ).first()

    if existing:
        existing.reaction = request.reaction
    else:
        reaction = CommentReaction(
            comment_id=comment_id, user_id=current_user.id,
            reaction=request.reaction
        )
        db.add(reaction)

    db.commit()
    return {"message": "Reaction added"}