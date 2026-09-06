import time
import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status, HTTPException
from src.app.core.config import settings
from src.app.core.security import decode_access_token
from src.app.core.broadcaster import broadcaster
from src.app.shared.dependencies import CurrentUser
from src.app.modules.realtime.schemas import CallTokenRequest, CallTokenResponse

router = APIRouter(tags=["Realtime"])

@router.websocket("/api/ws")
async def websocket_chat(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await broadcaster.connect(websocket)
    try:
        while True:
            # Keep the socket open and receive messages/ping
            await websocket.receive_text()
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

