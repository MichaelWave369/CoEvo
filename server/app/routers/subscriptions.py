from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..models import BoardSubscription, Board
from ..schemas import ToggleSubIn
from ..deps import get_current_user
from ..services.events_log import log_event

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

@router.get("/boards")
def get_board_subs(session: Session = Depends(get_session), user=Depends(get_current_user)):
    subs = session.exec(select(BoardSubscription).where(BoardSubscription.user_id==user.id)).all()
    return {"board_ids": [s.board_id for s in subs]}

@router.post("/boards/{board_id}")
def toggle_board_sub(board_id: int, payload: ToggleSubIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    b = session.get(Board, board_id)
    if not b:
        raise HTTPException(404, "Board not found")
    existing = session.exec(select(BoardSubscription).where(
        BoardSubscription.user_id==user.id,
        BoardSubscription.board_id==board_id
    )).first()

    if payload.subscribe:
        if existing:
            return {"ok": True}
        sub = BoardSubscription(user_id=user.id, board_id=board_id)
        session.add(sub)
        session.commit()
        log_event(session, "board_subscribed", {"user_id": user.id, "board_id": board_id})
        return {"ok": True}
    else:
        if existing:
            session.delete(existing)
            session.commit()
            log_event(session, "board_unsubscribed", {"user_id": user.id, "board_id": board_id})
        return {"ok": True}
