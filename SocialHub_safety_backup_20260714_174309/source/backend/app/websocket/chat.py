import json
from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set, Optional
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models.models import User, Chat, Message, MessageType
from ..utils.security import verify_token
from ..utils.time import isoformat_utc_z, utcnow_naive


class ConnectionManager:
    """Manage WebSocket connections for real-time chat."""

    def __init__(self):
        # user_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # chat_id -> set of user_ids
        self.chat_rooms: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        # Remove from all chat rooms
        for chat_id in list(self.chat_rooms.keys()):
            if user_id in self.chat_rooms[chat_id]:
                self.chat_rooms[chat_id].discard(user_id)
                if not self.chat_rooms[chat_id]:
                    del self.chat_rooms[chat_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

    async def broadcast_to_chat(self, chat_id: str, message: dict, exclude_user_id: str = None):
        if chat_id in self.chat_rooms:
            for user_id in self.chat_rooms[chat_id]:
                if user_id != exclude_user_id and user_id in self.active_connections:
                    await self.active_connections[user_id].send_json(message)

    def join_chat(self, chat_id: str, user_id: str):
        if chat_id not in self.chat_rooms:
            self.chat_rooms[chat_id] = set()
        self.chat_rooms[chat_id].add(user_id)

    def leave_chat(self, chat_id: str, user_id: str):
        if chat_id in self.chat_rooms:
            self.chat_rooms[chat_id].discard(user_id)
            if not self.chat_rooms[chat_id]:
                del self.chat_rooms[chat_id]


manager = ConnectionManager()


async def handle_chat_websocket(websocket: WebSocket, token: str):
    """Main WebSocket handler for chat functionality."""
    # Verify token
    payload = verify_token(token, "access")
    if payload is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload.get("sub")
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Connect
    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "join":
                # Join a chat room
                chat_id = data.get("chat_id")
                if chat_id:
                    manager.join_chat(chat_id, user_id)

                    # Send online status to chat
                    await manager.broadcast_to_chat(
                        chat_id,
                        {
                            "type": "user_online",
                            "user_id": user_id,
                            "timestamp": isoformat_utc_z(utcnow_naive())
                        },
                        exclude_user_id=user_id
                    )

            elif message_type == "leave":
                # Leave a chat room
                chat_id = data.get("chat_id")
                if chat_id:
                    manager.leave_chat(chat_id, user_id)

            elif message_type == "message":
                # Send a message
                chat_id = data.get("chat_id")
                content = data.get("content")
                message_type_str = data.get("message_type", "text")

                if chat_id and content:
                    # Save message to database
                    db = SessionLocal()
                    try:
                        message = Message(
                            chat_id=chat_id,
                            sender_id=user_id,
                            content=content,
                            message_type=MessageType.TEXT
                        )
                        db.add(message)

                        # Update chat timestamp
                        chat = db.query(Chat).filter(Chat.id == chat_id).first()
                        if chat:
                            chat.updated_at = utcnow_naive()

                        db.commit()
                        db.refresh(message)

                        # Broadcast message to all participants
                        message_data = {
                            "type": "new_message",
                            "message": {
                                "id": message.id,
                                "chat_id": message.chat_id,
                                "sender_id": message.sender_id,
                                "content": message.content,
                                "message_type": message.message_type.value,
                                "is_read": message.is_read,
                                "created_at": isoformat_utc_z(message.created_at)
                            },
                            "sender_id": user_id,
                            "timestamp": isoformat_utc_z(utcnow_naive())
                        }

                        await manager.broadcast_to_chat(chat_id, message_data)

                        # Also send to sender for confirmation
                        await manager.send_personal_message(message_data, user_id)

                    except Exception as e:
                        error_msg = {"type": "error", "message": str(e)}
                        await manager.send_personal_message(error_msg, user_id)
                    finally:
                        db.close()

            elif message_type == "typing":
                # Send typing indicator
                chat_id = data.get("chat_id")
                is_typing = data.get("is_typing", False)

                if chat_id:
                    await manager.broadcast_to_chat(
                        chat_id,
                        {
                            "type": "typing",
                            "user_id": user_id,
                            "is_typing": is_typing,
                            "timestamp": isoformat_utc_z(utcnow_naive())
                        },
                        exclude_user_id=user_id
                    )

            elif message_type == "read":
                # Mark messages as read
                chat_id = data.get("chat_id")

                if chat_id:
                    db = SessionLocal()
                    try:
                        messages = db.query(Message).filter(
                            Message.chat_id == chat_id,
                            Message.sender_id != user_id,
                            Message.is_read == False
                        ).all()

                        for msg in messages:
                            msg.is_read = True
                            msg.read_at = utcnow_naive()

                        db.commit()

                        # Notify sender that messages were read
                        await manager.broadcast_to_chat(
                            chat_id,
                            {
                                "type": "messages_read",
                                "user_id": user_id,
                                "chat_id": chat_id,
                                "timestamp": isoformat_utc_z(utcnow_naive())
                            },
                            exclude_user_id=user_id
                        )
                    finally:
                        db.close()

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        # Notify chat rooms that user is offline
        for chat_id in list(manager.chat_rooms.keys()):
            await manager.broadcast_to_chat(
                chat_id,
                {
                    "type": "user_offline",
                    "user_id": user_id,
                    "timestamp": isoformat_utc_z(utcnow_naive())
                }
            )
    except Exception as e:
        manager.disconnect(user_id)