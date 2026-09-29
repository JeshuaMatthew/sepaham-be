import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class Connection:
    """Satu koneksi websocket beserta identitas dan ruang langganannya.

    `user_id` wajib. Koneksi yang belum lewat verifikasi identitas TIDAK boleh
    menerima broadcast apa pun — kalau tidak, siapa pun yang bisa membuka socket
    ikut membaca semua pesan termasuk DM.
    """

    websocket: WebSocket
    user_id: uuid.UUID
    # Room yang sedang diamati: id channel, atau prefixed DM.
    # `None` = belum memilih ruang, hanya boleh menerima pesan global.
    room: str | None = None
    rooms: set[str] = field(default_factory=set)

    def subscribes(self, room: str | None) -> bool:
        return room in self.rooms


class Broadcaster:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, Connection] = {}

    async def connect(self, websocket: WebSocket, user_id: uuid.UUID) -> Connection:
        await websocket.accept()
        conn = Connection(websocket=websocket, user_id=user_id)
        self._connections[websocket] = conn
        return conn

    def register(self, websocket: WebSocket, user_id: uuid.UUID) -> Connection:
        """Pasang koneksi yang sudah `accept()`-ed (untuk jalur yang keduanya)."""
        conn = Connection(websocket=websocket, user_id=user_id)
        self._connections[websocket] = conn
        return conn

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)

    def subscribe(self, websocket: WebSocket, room: str) -> None:
        conn = self._connections.get(websocket)
        if conn is None:
            return
        conn.rooms.add(room)
        conn.room = room

    def unsubscribe_all(self, websocket: WebSocket) -> None:
        conn = self._connections.get(websocket)
        if conn is None:
            return
        conn.rooms.clear()
        conn.room = None

    def _recipients(self, room: str | None) -> list[WebSocket]:
        if room is None:
            return []
        return [ws for ws, conn in self._connections.items() if conn.subscribes(room)]

    async def broadcast(self, message: dict[str, Any], room: str | None = None) -> None:
        """Kirim `message` hanya ke koneksi yang berlangganan `room`.

        Tidak ada lagi "kirim ke semua". Room `None` tidak dikirim ke siapa pun,
        karena tanpa room tidak ada dasar untuk memutuskan siapa berhak melihat.
        """
        targets = self._recipients(room)
        if not targets:
            return

        message_json = json.dumps(message)
        dead: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_text(message_json)
            except Exception as exc:  # noqa: BLE001 - koneksi bisa mati kapan saja
                logger.debug("Gagal mengirim ke websocket: %s", exc)
                dead.append(websocket)
        for ws in dead:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


broadcaster = Broadcaster()
