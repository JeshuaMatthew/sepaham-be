import json
import time
import uuid

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.core.database import AsyncSessionLocal
from src.app.core.security import decode_access_token
from src.app.core.broadcaster import broadcaster
from src.app.shared.dependencies import CurrentUser
from src.app.modules.auth.entity import User
from src.app.modules.community.service import dm_room
from src.app.modules.community.entity import Channel, ServerMember, DirectConversation
from src.app.modules.realtime.schemas import CallTokenRequest, CallTokenResponse

router = APIRouter(tags=["Realtime"])


async def _authenticate_socket(websocket: WebSocket, token: str) -> uuid.UUID | None:
    """Decode token lalu pastikan user-nya benar-benar ada di database.

    Sebelumnya hanya `decode_access_token` yang dipanggil: token kedaluwarsa
    tidak di-rise, dan user yang sudah dihapus masih diterima. Kombinasi itu
    dengan `JWT_SECRET` default yang bisa ditebak membuat socket bisa dibuka
    siapa saja.
    """
    try:
        payload = decode_access_token(token)
    except Exception:
        return None

    sub = payload.get("sub")
    if not sub:
        return None

    try:
        user_uuid = uuid.UUID(sub)
    except ValueError:
        return None

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_uuid))
        if result.scalar_one_or_none() is None:
            return None

    return user_uuid


async def _resolve_room(db: AsyncSession, user_id: uuid.UUID, room: str) -> str | None:
    """Terjemahkan room dari klien ke nama room internal, atau None kalau
    pengguna tidak berhak."""

    if room.startswith("dm:"):
        dm_id = room[3:]
        try:
            dm_uuid = uuid.UUID(dm_id)
        except ValueError:
            return None
        res = await db.execute(
            select(DirectConversation.id).where(
                DirectConversation.id == dm_uuid,
                or_(
                    DirectConversation.user_low == user_id,
                    DirectConversation.user_high == user_id,
                ),
            )
        )
        return dm_room(dm_id) if res.scalar_one_or_none() else None

    res = await db.execute(select(Channel).where(Channel.id == room))
    channel = res.scalar_one_or_none()
    if channel is None:
        return None

    member = await db.execute(
        select(ServerMember).where(
            ServerMember.server_id == channel.server_id,
            ServerMember.user_id == user_id,
        )
    )
    return room if member.scalar_one_or_none() is not None else None


@router.websocket("/api/ws")
async def websocket_chat(websocket: WebSocket, token: str = Query(...)):
    user_id = await _authenticate_socket(websocket, token)
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    broadcaster.register(websocket, user_id)
    try:
        while True:
            raw = await websocket.receive_text()

            # Klien memberi tahu room mana yang sedang dibuka. Tanpa langganan
            # yang sah, koneksi tidak boleh menerima broadcast apa pun.
            try:
                message = json.loads(raw)
            except (TypeError, ValueError):
                continue

            if not isinstance(message, dict):
                continue

            if message.get("type") == "subscribe":
                room = message.get("room")
                if not isinstance(room, str) or not room:
                    continue
                async with AsyncSessionLocal() as session:
                    resolved = await _resolve_room(session, user_id, room)
                if resolved is not None:
                    broadcaster.subscribe(websocket, resolved)
            elif message.get("type") == "unsubscribe":
                broadcaster.unsubscribe_all(websocket)
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception:
        broadcaster.disconnect(websocket)

@router.post("/api/calls/token", response_model=CallTokenResponse, status_code=status.HTTP_200_OK)
async def generate_call_token(req: CallTokenRequest, user: CurrentUser):
    if not req.room or not req.room.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nama room tidak boleh kosong",
        )

    now_ts = int(time.time())
    payload = {
        "iss": settings.LIVEKIT_API_KEY,
        "sub": str(user.id),
        "name": user.name,
        "nbf": now_ts,
        "exp": now_ts + 6 * 3600,
        "video": {
            "roomJoin": True,
            "room": req.room.strip(),
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
        },
    }
    call_token = jwt.encode(payload, settings.LIVEKIT_API_SECRET, algorithm="HS256")

    return CallTokenResponse(
        token=call_token,
        url=settings.LIVEKIT_URL,
        identity=str(user.id),
        name=user.name,
        room=req.room.strip(),
    )

