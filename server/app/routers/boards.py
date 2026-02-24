from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ..db import get_session
from ..models import Board, BoardSubscription
from ..schemas import BoardOut, CreateBoardIn
from ..deps import get_current_user, require_role
from ..services.events_log import log_event

router = APIRouter(prefix="/api/boards", tags=["boards"])

@router.get("", response_model=list[BoardOut])
def list_boards(session: Session = Depends(get_session), user=Depends(get_current_user)):
    boards = session.exec(select(Board).order_by(Board.id)).all()
    subs = session.exec(select(BoardSubscription).where(BoardSubscription.user_id==user.id)).all()
    sub_ids = {s.board_id for s in subs}
    return [BoardOut(id=b.id, slug=b.slug, title=b.title, description=b.description, subscribed=(b.id in sub_ids)) for b in boards]

@router.post("", response_model=BoardOut)
def create_board(payload: CreateBoardIn, session: Session = Depends(get_session), _admin=Depends(require_role("admin","mod"))):
    b = Board(slug=payload.slug, title=payload.title, description=payload.description)
    session.add(b)
    session.commit()
    session.refresh(b)
    log_event(session, "board_created", {"board_id": b.id, "slug": b.slug})
    return BoardOut(id=b.id, slug=b.slug, title=b.title, description=b.description, subscribed=False)
