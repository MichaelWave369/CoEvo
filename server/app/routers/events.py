import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..core.events import broker

router = APIRouter(prefix="/api", tags=["events"])

@router.get("/events")
async def sse_events():
    async def gen():
        async for msg in broker.subscribe():
            yield f"event: message\ndata: {msg}\n\n"
            await asyncio.sleep(0)
    return StreamingResponse(gen(), media_type="text/event-stream")
