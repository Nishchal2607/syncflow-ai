import json
<<<<<<< HEAD
import asyncio
=======
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(session_id, []).append(ws)

    def disconnect(self, session_id: str, ws: WebSocket):
        conns = self.active.get(session_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns and session_id in self.active:
            del self.active[session_id]

    async def broadcast(self, session_id: str, message: dict):
        conns = self.active.get(session_id, [])
        dead = []
        payload = json.dumps(message, default=str)
<<<<<<< HEAD
        for ws in list(conns):
            try:
                await asyncio.wait_for(ws.send_text(payload), timeout=2)
=======
        for ws in conns:
            try:
                await ws.send_text(payload)
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
            except Exception:
                dead.append(ws)
        for d in dead:
            self.disconnect(session_id, d)


manager = ConnectionManager()
