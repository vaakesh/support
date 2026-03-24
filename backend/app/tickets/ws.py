





from collections import defaultdict
from functools import lru_cache
import logging
from uuid import UUID

from fastapi import Depends, WebSocket

from app.tickets.deps import get_message_service
from app.tickets.service import MessageService

logger = logging.getLogger(__name__)

class ConnectionManager:

    def __init__(self):
        logger.info("CREATING CONNECTION MANAGER")
        self.active_connections: dict[UUID, list[WebSocket]] = defaultdict(list)
    
    async def connect(self, ticket_uuid: UUID, ws: WebSocket) -> None:
        await ws.accept()
        self.active_connections[ticket_uuid].append(ws)

    def disconnect(self, ticket_uuid: UUID, ws: WebSocket) -> None:
        connections = self.active_connections[ticket_uuid]
        if ws in connections:
            connections.remove(ws)

        if not connections:
            del self.active_connections[ticket_uuid]

    async def broadcast(self, ticket_uuid: str, data: dict, sender: WebSocket = None) -> None:
        for ws in list(self.active_connections.get(ticket_uuid, [])):
            try:
                if ws != sender:
                    await ws.send_json(data)
            except Exception:
                pass
    

@lru_cache
def get_connection_manager():
    return ConnectionManager()