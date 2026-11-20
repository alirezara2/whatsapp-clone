import asyncio
import json
from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    """
    مدیریت اتصالهای WebSocket.
    chat_id → set of (user_id, websocket)
    """

    def __init__(self):
        self.rooms: dict[int, set[tuple[int, WebSocket]]] = defaultdict(set)
        self.lock = asyncio.Lock()

    async def connect(self, chat_id: int, user_id: int, ws: WebSocket):
        await ws.accept()
        async with self.lock:
            self.rooms[chat_id].add((user_id, ws))

    async def disconnect(self, chat_id: int, user_id: int, ws: WebSocket):
        async with self.lock:
            self.rooms[chat_id].discard((user_id, ws))
            if not self.rooms[chat_id]:
                self.rooms.pop(chat_id, None)

    async def broadcast(self, chat_id: int, payload: dict, exclude_ws: WebSocket | None = None):
        """پیام رو به همه اعضای چت میفرسته (به جز فرستنده اگه exclude_ws بذاریم)."""
        message = json.dumps(payload, default=str, ensure_ascii=False)
        dead: list[tuple[int, WebSocket]] = []
        async with self.lock:
            targets = list(self.rooms.get(chat_id, set()))
        for uid, ws in targets:
            if ws is exclude_ws:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                dead.append((uid, ws))
        for uid, ws in dead:
            await self.disconnect(chat_id, uid, ws)

    def is_online(self, chat_id: int, user_id: int) -> bool:
        return any(uid == user_id for uid, _ in self.rooms.get(chat_id, set()))


manager = ConnectionManager()