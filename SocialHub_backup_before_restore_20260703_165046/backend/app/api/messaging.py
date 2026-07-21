from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models.models import (
    User, Chat, Message, MessageReaction, Notification, MessageType, chat_participants
)
from ..schemas.schemas import (
    ChatResponse, MessageResponse, SendMessageRequest, CreateChatRequest,
    UserSearchResult, DeleteMessageRequest, MessageReactionRequest
)
from ..utils.dependencies import get_current_user, save_upload_file, validate_audio_file
from ..config import settings

router = APIRouter(prefix="/api/chats", tags=["Messaging"])


def build_message_response(msg, db):
    """Build MessageResponse with sender info and reactions."""
    sender_data = None
    if msg.sender:
        pp = msg.sender.profile_picture if hasattr(msg.sender, 'profile_picture') else None
        sender_data = UserSearchResult(
            id=msg.sender.id, username=msg.sender.username, full_name=msg.sender.full_name,
            profile_picture=pp, is_verified=msg.sender.is_verified,
            followers_count=msg.sender.followers_count, badge=getattr(msg.sender, 'badge', None)
        )

    reactions = []
    for r in msg.reactions:
        reactions.append({"id": r.id, "user_id": r.user_id, "reaction": r.reaction, "created_at": r.created_at})

    return MessageResponse(
        id=msg.id, chat_id=msg.chat_id, sender_id=msg.sender_id,
        content=msg.content, message_type=msg.message_type,
        file_url=msg.file_url, is_read=msg.is_read,
        is_deleted=getattr(msg, 'is_deleted', False),
        read_at=msg.read_at, created_at=msg.created_at,
        sender=sender_data, reactions=reactions
    )


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    request: CreateChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat (private or group)."""
    all_participants = list(set([current_user.id] + request.participant_ids))

    if not request.is_group and len(all_participants) == 2:
        existing_chats = db.query(Chat).filter(Chat.is_group == False).all()
        for chat in existing_chats:
            chat_user_ids = [p.id for p in chat.participants]
            if set(chat_user_ids) == set(all_participants):
                return chat

    chat = Chat(name=request.name, is_group=request.is_group, created_by=current_user.id)
    db.add(chat)
    db.flush()

    for user_id in all_participants:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            chat.participants.append(user)

    db.commit()
    db.refresh(chat)
    return chat


@router.get("", response_model=List[ChatResponse])
def get_user_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all chats for current user."""
    chats = db.query(Chat).filter(
        Chat.participants.any(User.id == current_user.id)
    ).order_by(Chat.updated_at.desc()).all()

    result = []
    for chat in chats:
        last_message = db.query(Message).filter(
            Message.chat_id == chat.id
        ).order_by(Message.created_at.desc()).first()

        unread_count = db.query(Message).filter(
            Message.chat_id == chat.id, Message.sender_id != current_user.id, Message.is_read == False
        ).count()

        participants = []
        for user in chat.participants:
            pp = user.profile_picture if hasattr(user, 'profile_picture') else None
            participants.append(UserSearchResult(
                id=user.id, username=user.username, full_name=user.full_name,
                profile_picture=pp, is_verified=user.is_verified,
                followers_count=user.followers_count, badge=getattr(user, 'badge', None)
            ))

        last_msg = build_message_response(last_message, db) if last_message else None

        result.append(ChatResponse(
            id=chat.id, name=chat.name, is_group=chat.is_group,
            created_by=chat.created_by, created_at=chat.created_at,
            last_message=last_msg, participants=participants, unread_count=unread_count
        ))

    return result


@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat(chat_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get chat details."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if current_user.id not in [p.id for p in chat.participants]:
        raise HTTPException(status_code=403, detail="Not a participant")
    return chat


@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
def get_chat_messages(
    chat_id: str, page: int = 1, page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages for a chat."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if current_user.id not in [p.id for p in chat.participants]:
        raise HTTPException(status_code=403, detail="Not a participant")

    offset = (page - 1) * page_size
    messages = db.query(Message).filter(
        Message.chat_id == chat_id, Message.deleted_for_all == False
    ).order_by(Message.created_at.desc()).offset(offset).limit(page_size).all()

    # Mark messages as read
    for msg in messages:
        if msg.sender_id != current_user.id and not msg.is_read:
            msg.is_read = True
            msg.read_at = datetime.utcnow()
    db.commit()

    return [build_message_response(msg, db) for msg in messages]


@router.post("/{chat_id}/messages", response_model=MessageResponse)
def send_message(
    chat_id: str, request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a text message."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if current_user.id not in [p.id for p in chat.participants]:
        raise HTTPException(status_code=403, detail="Not a participant")

    message = Message(
        chat_id=chat_id, sender_id=current_user.id,
        content=request.content, message_type=request.message_type
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return build_message_response(message, db)


@router.post("/{chat_id}/files", response_model=MessageResponse)
async def send_file_message(
    chat_id: str, file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a file/image/voice message."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if current_user.id not in [p.id for p in chat.participants]:
        raise HTTPException(status_code=403, detail="Not a participant")

    content_type = file.content_type or ""
    if validate_audio_file(file):
        msg_type = "voice"
    elif content_type.startswith("image"):
        msg_type = "image"
    else:
        msg_type = "file"

    file_path = await save_upload_file(settings.UPLOAD_DIR, file, "chat_files")

    message = Message(
        chat_id=chat_id, sender_id=current_user.id,
        content=file.filename, message_type=msg_type, file_url=file_path
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return build_message_response(message, db)


@router.put("/messages/{message_id}/read")
def mark_message_read(message_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a message as read."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.commit()
    return {"message": "Message marked as read"}


@router.post("/messages/{message_id}/react")
def react_to_message(
    message_id: str, request: MessageReactionRequest,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """React to a message."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    existing = db.query(MessageReaction).filter(
        MessageReaction.message_id == message_id, MessageReaction.user_id == current_user.id
    ).first()

    if existing:
        existing.reaction = request.reaction
    else:
        reaction = MessageReaction(message_id=message_id, user_id=current_user.id, reaction=request.reaction)
        db.add(reaction)

    db.commit()
    return {"message": "Reaction added"}


@router.delete("/messages/{message_id}")
def delete_message(
    message_id: str, request: DeleteMessageRequest = DeleteMessageRequest(),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Delete a message."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if request.delete_for_all:
        if message.sender_id != current_user.id:
            raise HTTPException(status_code=403, detail="Can only delete your own messages")
        message.deleted_for_all = True
        message.content = "This message has been deleted"
    else:
        message.is_deleted = True

    db.commit()
    return {"message": "Message deleted"}


@router.get("/{chat_id}/search")
def search_chat_messages(
    chat_id: str, q: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search messages in a chat."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if current_user.id not in [p.id for p in chat.participants]:
        raise HTTPException(status_code=403, detail="Not a participant")

    messages = db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.content.ilike(f"%{q}%"),
        Message.deleted_for_all == False
    ).order_by(Message.created_at.desc()).limit(50).all()

    return [build_message_response(msg, db) for msg in messages]


@router.post("/{chat_id}/typing")
def set_typing_indicator(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set typing indicator for a chat."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if current_user.id not in [p.id for p in chat.participants]:
        raise HTTPException(status_code=403, detail="Not a participant")
    # In production, use Redis/WebSocket to broadcast typing status
    return {"message": "Typing indicator set", "chat_id": chat_id, "user_id": current_user.id}
