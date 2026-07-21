from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

from ..database import SessionLocal
from ..models.models import LiveStream, LiveChatMessage, User
from ..utils.security import verify_token
from ..utils.time import isoformat_utc_z, utcnow_naive


class LiveConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.users: Dict[WebSocket, str] = {}

    async def connect(self, live_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.rooms.setdefault(live_id, set()).add(websocket)
        self.users[websocket] = user_id

    def disconnect(self, live_id: str, websocket: WebSocket):
        if live_id in self.rooms:
            self.rooms[live_id].discard(websocket)
            if not self.rooms[live_id]:
                del self.rooms[live_id]
        self.users.pop(websocket, None)

    async def broadcast(self, live_id: str, payload: dict):
        for ws in list(self.rooms.get(live_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(live_id, ws)


live_manager = LiveConnectionManager()


async def handle_live_websocket(websocket: WebSocket, live_id: str, token: str):
    payload = verify_token(token, "access")
    user_id = payload.get("sub") if payload else None
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    live = db.query(LiveStream).filter(LiveStream.id == live_id, LiveStream.is_deleted == False).first()
    if not user or not live:
        db.close()
        await websocket.close(code=4004, reason="Live stream not found")
        return
    db.close()

    await live_manager.connect(live_id, user_id, websocket)
    await live_manager.broadcast(live_id, {
        "type": "user_joined",
        "user_id": user_id,
        "username": user.username,
        "timestamp": isoformat_utc_z(utcnow_naive()),
    })

    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            now = isoformat_utc_z(utcnow_naive())
            if event_type == "chat_message":
                text = (data.get("message") or data.get("content") or "").strip()
                if not text:
                    continue
                db = SessionLocal()
                try:
                    msg = LiveChatMessage(live_id=live_id, user_id=user_id, message=text[:1000])
                    db.add(msg)
                    db.commit()
                    db.refresh(msg)
                    await live_manager.broadcast(live_id, {
                        "type": "chat_message",
                        "id": msg.id,
                        "user_id": user_id,
                        "username": user.username,
                        "message": msg.message,
                        "created_at": isoformat_utc_z(msg.created_at),
                    })
                finally:
                    db.close()
            elif event_type in {"live_like", "live_gift", "camera_status"}:
                payload = {"type": event_type, "user_id": user_id, "timestamp": now}
                payload.update({k: v for k, v in data.items() if k != "type"})
                await live_manager.broadcast(live_id, payload)
    except WebSocketDisconnect:
        pass
    finally:
        live_manager.disconnect(live_id, websocket)
        await live_manager.broadcast(live_id, {
            "type": "user_left",
            "user_id": user_id,
            "timestamp": isoformat_utc_z(utcnow_naive()),
        })
