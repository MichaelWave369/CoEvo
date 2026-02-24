from datetime import datetime
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ..db import get_session
from ..models import Notification
from ..schemas import MarkReadIn
from ..deps import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("")
def list_notifications(session: Session = Depends(get_session), user=Depends(get_current_user), limit: int = 50):
    q = select(Notification).where(Notification.user_id==user.id).order_by(Notification.id.desc()).limit(limit)
    items = session.exec(q).all()
    return [{
        "id": n.id,
        "thread_id": n.thread_id,
        "event_type": n.event_type,
        "payload": n.payload,
        "created_at": n.created_at.isoformat()+"Z",
        "read_at": n.read_at.isoformat()+"Z" if n.read_at else None
    } for n in items]

@router.get("/unread-count")
def unread_count(session: Session = Depends(get_session), user=Depends(get_current_user)):
    q = select(Notification).where(Notification.user_id==user.id, Notification.read_at==None)
    items = session.exec(q).all()
    return {"count": len(items)}

@router.patch("/{notif_id}/read")
def mark_read(notif_id: int, payload: MarkReadIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    n = session.get(Notification, notif_id)
    if not n or n.user_id != user.id:
        return {"ok": False}
    n.read_at = datetime.utcnow() if payload.read else None
    session.add(n)
    session.commit()
    return {"ok": True}
