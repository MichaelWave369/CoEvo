import asyncio
import json
from typing import Any, AsyncGenerator

class EventBroker:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    async def publish(self, event: dict[str, Any]) -> None:
        msg = json.dumps(event, ensure_ascii=False)
        async with self._lock:
            dead = []
            for q in self._subscribers:
                try:
                    q.put_nowait(msg)
                except Exception:
                    dead.append(q)
            for q in dead:
                self._subscribers.discard(q)

    async def subscribe(self) -> AsyncGenerator[str, None]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
        async with self._lock:
            self._subscribers.add(q)
        try:
            yield json.dumps({"type": "keepalive"})
            while True:
                msg = await q.get()
                yield msg
        finally:
            async with self._lock:
                self._subscribers.discard(q)

broker = EventBroker()
