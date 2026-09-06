import json
import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class Broadcaster:
    def __init__(self):
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]):
        message_json = json.dumps(message)
        dead_connections = []
        for connection in list(self._connections):
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.debug(f'Failed to send to websocket: {e}')
                dead_connections.append(connection)
        for dc in dead_connections:
            self._connections.discard(dc)

broadcaster = Broadcaster()
