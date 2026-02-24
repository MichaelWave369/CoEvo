from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from ..db import get_session
from ..models import Post, PostReport, Thread
from ..schemas import ReportPostIn, HidePostIn
from ..deps import get_current_user, require_role
from ..core.events import broker
from ..services.events_log import log_event

router = APIRouter(prefix="/api/mod", tags=["moderation"])

@router.post("/posts/{post_id}/report")
async def report_post(post_id: int, payload: ReportPostIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    p = session.get(Post, post_id)
    if not p:
        raise HTTPException(404, "Post not found")
    r = PostReport(post_id=post_id, reporter_user_id=user.id, reason=payload.reason or "")
    session.add(r)
    session.commit()
    log_event(session, "post_reported", {"post_id": post_id, "by": user.handle})
    await broker.publish({"type":"post_reported","post_id":post_id})
    return {"ok": True}

@router.post("/posts/{post_id}/hide")
async def hide_post(post_id: int, payload: HidePostIn, session: Session = Depends(get_session), _mod=Depends(require_role("admin","mod"))):
    p = session.get(Post, post_id)
    if not p:
        raise HTTPException(404, "Post not found")
    p.is_hidden = bool(payload.hide)
    session.add(p)
    t = session.get(Thread, p.thread_id)
    if t:
        session.add(t)
    session.commit()
    log_event(session, "post_hidden_toggled", {"post_id": post_id, "hide": p.is_hidden})
    await broker.publish({"type":"post_hidden","post_id":post_id,"hide":p.is_hidden,"thread_id":p.thread_id})
    return {"ok": True, "is_hidden": p.is_hidden}
