from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ..db import get_session
from ..deps import get_current_user
from ..models import Board, Thread

router = APIRouter(prefix='/api', tags=['developer-api'])

@router.get('/docs')
def api_docs(user=Depends(get_current_user)):
    return {
        "title": "CoEvo Public API",
        "auth": "Bearer token (use /api/auth/login)",
        "endpoints": [
            {"method": "GET", "path": "/api/public-api/boards", "desc": "List boards"},
            {"method": "GET", "path": "/api/public-api/threads/{board_id}", "desc": "List threads for a board"},
            {"method": "GET", "path": "/api/public-api/health", "desc": "API health"},
        ],
    }

@router.get('/public-api/health')
def public_health(user=Depends(get_current_user)):
    return {"ok": True, "scope": "public-api"}

@router.get('/public-api/boards')
def public_boards(session: Session = Depends(get_session), user=Depends(get_current_user)):
    boards = session.exec(select(Board).order_by(Board.id)).all()
    return [{"id":b.id, "slug":b.slug, "title":b.title, "description":b.description, "is_premium": b.is_premium} for b in boards]

@router.get('/public-api/threads/{board_id}')
def public_threads(board_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    threads = session.exec(select(Thread).where(Thread.board_id==board_id).order_by(Thread.updated_at.desc())).all()
    return [{"id":t.id, "title":t.title, "board_id": t.board_id, "updated_at": t.updated_at.isoformat()+"Z"} for t in threads]
