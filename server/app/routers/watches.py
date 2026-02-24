from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..models import ThreadWatch, Thread
from ..schemas import ToggleWatchIn
from ..deps import get_current_user
from ..services.events_log import log_event

router = APIRouter(prefix="/api/watches", tags=["watches"])

@router.get("/thread/{thread_id}")
def watch_status(thread_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    w = session.exec(select(ThreadWatch).where(ThreadWatch.user_id==user.id, ThreadWatch.thread_id==thread_id)).first()
    return {"watching": bool(w)}

@router.post("/thread/{thread_id}")
def toggle_watch(thread_id: int, payload: ToggleWatchIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    t = session.get(Thread, thread_id)
    if not t:
        raise HTTPException(404, "Thread not found")
    w = session.exec(select(ThreadWatch).where(ThreadWatch.user_id==user.id, ThreadWatch.thread_id==thread_id)).first()
    if payload.watch:
        if not w:
            w = ThreadWatch(user_id=user.id, thread_id=thread_id)
            session.add(w)
            session.commit()
            log_event(session, "thread_watched", {"user_id": user.id, "thread_id": thread_id})
        return {"ok": True, "watching": True}
    else:
        if w:
            session.delete(w)
            session.commit()
            log_event(session, "thread_unwatched", {"user_id": user.id, "thread_id": thread_id})
        return {"ok": True, "watching": False}
