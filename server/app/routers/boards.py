from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..models import Board, BoardSubscription, User
from ..schemas import BoardOut, CreateBoardIn
from ..deps import get_current_user
from ..services.events_log import log_event

router = APIRouter(prefix="/api/boards", tags=["boards"])

PREMIUM_BOARD_REP = 200

@router.get("", response_model=list[BoardOut])
def list_boards(session: Session = Depends(get_session), user=Depends(get_current_user)):
    boards = session.exec(select(Board).order_by(Board.id)).all()
    subs = session.exec(select(BoardSubscription).where(BoardSubscription.user_id==user.id)).all()
    sub_ids = {s.board_id for s in subs}
    return [BoardOut(id=b.id, slug=b.slug, title=b.title, description=b.description, is_premium=b.is_premium, subscribed=(b.id in sub_ids)) for b in boards]

@router.post("", response_model=BoardOut)
def create_board(payload: CreateBoardIn, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    if payload.is_premium and user.reputation < PREMIUM_BOARD_REP:
        raise HTTPException(403, f"Premium boards require reputation >= {PREMIUM_BOARD_REP}")
    exists = session.exec(select(Board).where(Board.slug==payload.slug)).first()
    if exists:
        raise HTTPException(400, "Slug already exists")
    b = Board(slug=payload.slug, title=payload.title, description=payload.description, is_premium=payload.is_premium)
    session.add(b)
    session.commit()
    session.refresh(b)
    log_event(session, "board_created", {"board_id": b.id, "slug": b.slug, "is_premium": b.is_premium, "by": user.handle})
    return BoardOut(id=b.id, slug=b.slug, title=b.title, description=b.description, is_premium=b.is_premium, subscribed=False)
