from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from ..database import get_db
from ..models.models import (
    User, Chat, Message, MessageReaction, Notification, MessageType, chat_participants,
    UserOnlineStatus, DeletedMessage
)
from ..schemas.schemas import (
    ChatResponse, MessageResponse, SendMessageRequest, CreateChatRequest,
    UserSearchResult, DeleteMessageRequest, MessageReactionRequest
)
from ..utils.dependencies import get_current_user, save_upload_file, validate_audio_file
from ..config import settings
from ..utils.time import utcnow_naive

router = APIRouter(prefix="/api/chats", tags=["Messaging"])


def user_to_search_result(user: User) -> UserSearchResult:
    return UserSearchResult(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        profile_picture=user.profile_picture if hasattr(user, 'profile_picture') else None,
        is_verified=user.is_verified,
        followers_count=user.followers_count,
        badge=getattr(user, 'badge', None)
    )


def get_chat_participant_ids(chat: Chat) -> List[str]:
    return [p.id for p in chat.participants]


def get_other_private_participant(chat: Chat, current_user_id: str) -> Optional[User]:
    return next((p for p in chat.participants if p.id != current_user_id), None)


def find_or_create_private_chat(db: Session, current_user: User, other_user_id: str) -> Chat:
    if other_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot chat with yourself")
    other_user = db.query(User).filter(
        User.id == other_user_id,
        User.is_active == True,
        User.is_banned == False
    ).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_chats = db.query(Chat).filter(Chat.is_group == False).all()
    wanted = {current_user.id, other_user_id}
    for chat in existing_chats:
        if set(get_chat_participant_ids(chat)) == wanted:
            return chat

    chat = Chat(is_group=False, created_by=current_user.id)
    db.add(chat)
    db.flush()
    chat.participants.append(current_user)
    chat.participants.append(other_user)
    db.commit()
    db.refresh(chat)
    return chat


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
        receiver_id=getattr(msg, 'receiver_id', None),
        content=msg.content or getattr(msg, 'message_text', None),
        message_text=getattr(msg, 'message_text', None) or msg.content,
        message_type=msg.message_type,
        file_url=msg.file_url, is_read=msg.is_read,
        is_deleted=getattr(msg, 'is_deleted', False),
        read_at=msg.read_at, created_at=msg.created_at,
        updated_at=getattr(msg, 'updated_at', None) or msg.created_at,
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
                return build_chat_response(chat, current_user.id, db)

    chat = Chat(name=request.name, is_group=request.is_group, created_by=current_user.id)
    db.add(chat)
    db.flush()

    for user_id in all_participants:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            chat.participants.append(user)

    db.commit()
    db.refresh(chat)
    return build_chat_response(chat, current_user.id, db)


def build_chat_response(chat: Chat, current_user_id: str, db: Session) -> ChatResponse:
    last_message = db.query(Message).filter(
        Message.chat_id == chat.id,
        Message.deleted_for_all == False
    ).order_by(Message.created_at.desc()).first()

    unread_count = db.query(Message).filter(
        Message.chat_id == chat.id,
        Message.sender_id != current_user_id,
        Message.is_read == False,
        Message.deleted_for_all == False
    ).count()

    return ChatResponse(
        id=chat.id,
        name=chat.name,
        is_group=chat.is_group,
        created_by=chat.created_by,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        last_message=build_message_response(last_message, db) if last_message else None,
        participants=[user_to_search_result(user) for user in chat.participants],
        unread_count=unread_count
    )


@router.get("", response_model=List[ChatResponse])
def get_user_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all chats for current user."""
    chats = db.query(Chat).filter(
        Chat.participants.any(User.id == current_user.id)
    ).order_by(Chat.updated_at.desc()).all()

    return [build_chat_response(chat, current_user.id, db) for chat in chats]


@router.get("/users", response_model=List[UserSearchResult])
def get_chat_users(
    q: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """GET all searchable chat users, optionally filtered by name/username."""
    query = db.query(User).filter(
        User.id != current_user.id,
        User.is_active == True,
        User.is_banned == False
    )
    if q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(or_(User.username.ilike(term), User.full_name.ilike(term)))
    return [user_to_search_result(user) for user in query.order_by(User.username.asc()).limit(50).all()]


@router.post("/direct/{user_id}", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_or_get_direct_chat(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or return a one-to-one chat with a selected user."""
    chat = find_or_create_private_chat(db, current_user, user_id)
    return build_chat_response(chat, current_user.id, db)


@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat(chat_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get chat details."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if current_user.id not in [p.id for p in chat.participants]:
        raise HTTPException(status_code=403, detail="Not a participant")
    return build_chat_response(chat, current_user.id, db)


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
            msg.read_at = utcnow_naive()
    db.commit()

    return [build_message_response(msg, db) for msg in reversed(messages)]


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

    text = (request.content or request.message_text or "").strip()
    if not text and request.message_type == "text":
        raise HTTPException(status_code=400, detail="Message text is required")
    receiver_id = request.receiver_id
    if not receiver_id and not chat.is_group:
        other = get_other_private_participant(chat, current_user.id)
        receiver_id = other.id if other else None

    message = Message(
        chat_id=chat_id, sender_id=current_user.id, receiver_id=receiver_id,
        content=text, message_text=text, message_type=request.message_type
    )
    db.add(message)
    for participant in chat.participants:
        if participant.id != current_user.id:
            db.add(Notification(
                user_id=participant.id,
                actor_id=current_user.id,
                type="message",
                message=f"{current_user.username} sent you a message",
                reference_id=chat_id,
                reference_type="chat"
            ))
    chat.updated_at = utcnow_naive()
    db.commit()
    db.refresh(message)
    return build_message_response(message, db)


@router.get("/with/{user_id}/messages", response_model=List[MessageResponse])
def get_messages_between_two_users(
    user_id: str,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """GET messages between current user and another user."""
    chat = find_or_create_private_chat(db, current_user, user_id)
    return get_chat_messages(chat.id, page, page_size, current_user, db)


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
    chat = db.query(Chat).filter(Chat.id == message.chat_id).first()
    if not chat or current_user.id not in get_chat_participant_ids(chat):
        raise HTTPException(status_code=403, detail="Not a participant")
    if message.sender_id == current_user.id:
        return {"message": "Own message does not need read marking"}
    if not message.is_read:
        message.is_read = True
        message.read_at = utcnow_naive()
        db.commit()
    return {"message": "Message marked as read"}


@router.put("/{chat_id}/read")
def mark_chat_read(chat_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark all unread messages in a chat as read."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if current_user.id not in get_chat_participant_ids(chat):
        raise HTTPException(status_code=403, detail="Not a participant")
    count = 0
    for msg in db.query(Message).filter(Message.chat_id == chat_id, Message.sender_id != current_user.id, Message.is_read == False).all():
        msg.is_read = True
        msg.read_at = utcnow_naive()
        count += 1
    db.commit()
    return {"message": "Chat marked as read", "updated": count}


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
        if message.sender_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Can only delete your own messages")
        message.deleted_for_all = True
        message.content = "This message has been deleted"
    else:
        if message.sender_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Can only delete your own messages")
        message.is_deleted = True
    message.deleted_at = utcnow_naive()

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


@router.get("/online-status/{user_id}")
def get_online_status(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get online status for a user."""
    status_obj = db.query(UserOnlineStatus).filter(UserOnlineStatus.user_id == user_id).first()
    if not status_obj:
        return {"user_id": user_id, "is_online": False, "last_seen": None}
    return {
        "user_id": user_id,
        "is_online": status_obj.is_online,
        "last_seen": str(status_obj.last_seen),
    }


@router.post("/online-status")
def set_online_status(
    is_online: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set current user's online status."""
    status_obj = db.query(UserOnlineStatus).filter(UserOnlineStatus.user_id == current_user.id).first()
    if not status_obj:
        status_obj = UserOnlineStatus(user_id=current_user.id, is_online=is_online)
        db.add(status_obj)
    else:
        status_obj.is_online = is_online
        status_obj.last_seen = utcnow_naive()
    db.commit()
    return {"message": "Status updated", "is_online": is_online}


@router.put("/messages/{message_id}/seen")
def mark_message_seen(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark message as seen."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.sender_id == current_user.id:
        return {"message": "Cannot mark own message as seen"}
    
    message.is_read = True
    message.read_at = utcnow_naive()
    db.commit()
    return {"message": "Message marked as seen", "read_at": str(message.read_at)}


@router.put("/messages/{message_id}/delete-me")
def delete_message_for_me(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete message for current user only."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    existing = db.query(DeletedMessage).filter(
        DeletedMessage.user_id == current_user.id,
        DeletedMessage.message_id == message_id
    ).first()
    if not existing:
        dm = DeletedMessage(user_id=current_user.id, message_id=message_id)
        db.add(dm)
    db.commit()
    return {"message": "Message deleted for you"}


@router.put("/messages/{message_id}/delete-all")
def delete_message_for_all(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete message for everyone (only sender can do this)."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only sender can delete for everyone")
    
    message.deleted_for_all = True
    message.content = "This message has been deleted"
    db.commit()
    return {"message": "Message deleted for everyone"}
