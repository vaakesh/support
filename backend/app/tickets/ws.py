





import asyncio
from collections import defaultdict
from functools import lru_cache
import json
import logging
from uuid import UUID
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from fastapi import Depends, Request, WebSocket

from app.deps import get_redis

logger = logging.getLogger(__name__)

class ConnectionManager:

    def __init__(self, redis: Redis):
        self.active_connections: dict[str, list[tuple[WebSocket, str]]] = defaultdict(list) # ["ticket_uuid"] = (WebSocket, user_uuid)
        self.redis: Redis = redis
        self.pubsub: PubSub = redis.pubsub()
        logger.info(f"created connection manager:\n{self.redis}\n{self.pubsub}")

    # подписываемся на все тикеты и начинаем слушать сообщения
    async def startup(self):
        await self.pubsub.psubscribe("ticket:*")
        asyncio.create_task(self._listen())

    # слушаем сообщения
    async def _listen(self):
        async for message in self.pubsub.listen():
            logger.info(f"got message = {message}")
            if message["type"] != "pmessage":
                continue

            channel = message["channel"] # "ticket:ticket_uuid"
            ticket_uuid = channel.split(":", 1)[1]
            data = json.loads(message["data"])
            await self._broadcast_local(ticket_uuid, data) # рассылает сообщения локальным соединениям в каждом воркере
    
    async def connect(self, ticket_uuid: str, ws: WebSocket, user_uuid: str) -> None:
        await ws.accept()
        self.active_connections[ticket_uuid].append((ws, user_uuid))
        logger.info(f"active connections: {self.active_connections}")

    def disconnect(self, ticket_uuid: str, ws: WebSocket, user_uuid: str) -> None:
        connections = self.active_connections[ticket_uuid]
        ws_connections = [connection[0] for connection in connections]
        if ws in ws_connections:
            connections.remove((ws, user_uuid))

        if not connections:
            del self.active_connections[ticket_uuid]
        

    async def broadcast(self, ticket_uuid: str, data: dict, ws: WebSocket) -> None:
        data["ws"] = str(ws)
        await self.redis.publish(f"ticket:{ticket_uuid}", json.dumps(data))

    async def _broadcast_local(self, ticket_uuid: str, data: dict) -> None:
        current_connections = list(self.active_connections.get(ticket_uuid, []))
        for ws, user_uuid in current_connections:
            try:
                if data["ws"] == str(ws):
                    continue
                new_data = {"type": data["type"], "message": data["payload"], "username": data["username"]}
                logger.info(f"sending {new_data} to {ws}")
                await ws.send_json(new_data)
            except:
                raise

def get_connection_manager(ws: WebSocket) -> ConnectionManager:
    return ws.app.state.connection_manager