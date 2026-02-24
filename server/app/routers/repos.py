from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ..db import get_session
from ..models import RepoLink
from ..schemas import CreateRepoIn
from ..deps import get_current_user
from ..services.events_log import log_event

router = APIRouter(prefix="/api/repos", tags=["repos"])

@router.get("")
def list_repos(session: Session = Depends(get_session), user=Depends(get_current_user)):
    repos = session.exec(select(RepoLink).order_by(RepoLink.id.desc())).all()
    return [{
        "id": r.id, "url": r.url, "title": r.title, "description": r.description,
        "tags": r.tags, "created_at": r.created_at.isoformat()+"Z"
    } for r in repos]

@router.post("")
def add_repo(payload: CreateRepoIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    r = RepoLink(url=payload.url, title=payload.title, description=payload.description, tags=payload.tags, added_by_user_id=user.id)
    session.add(r)
    session.commit()
    session.refresh(r)
    log_event(session, "repo_added", {"repo_id": r.id, "by": user.handle, "url": r.url})
    return {"id": r.id}
