from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..deps import get_current_user
from ..models import Post, PostReaction
from ..schemas import ReactIn
from ..core.events import broker

router = APIRouter(prefix='/api/reactions', tags=['reactions'])

@router.get('/post/{post_id}')
def list_reactions(post_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    rows = session.exec(select(PostReaction).where(PostReaction.post_id==post_id)).all()
    counts = {}
    for r in rows:
        counts[r.reaction] = counts.get(r.reaction, 0) + 1
    return {'post_id': post_id, 'counts': counts}

@router.post('/post/{post_id}')
async def react(post_id: int, payload: ReactIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    p = session.get(Post, post_id)
    if not p:
        raise HTTPException(404, 'Post not found')
    existing = session.exec(select(PostReaction).where(PostReaction.post_id==post_id, PostReaction.by_user_id==user.id, PostReaction.reaction==payload.reaction)).first()
    if existing:
        session.delete(existing)
        session.commit()
        rows = session.exec(select(PostReaction).where(PostReaction.post_id==post_id)).all()
        counts = {}
        for r in rows: counts[r.reaction] = counts.get(r.reaction,0)+1
        await broker.publish({'type':'reaction_updated','thread_id': p.thread_id, 'post_id': post_id, 'counts': counts})
        return {'ok': True, 'toggled_off': True}
    row = PostReaction(post_id=post_id, reaction=payload.reaction, by_user_id=user.id)
    session.add(row)
    session.commit()
    rows = session.exec(select(PostReaction).where(PostReaction.post_id==post_id)).all()
    counts = {}
    for r in rows: counts[r.reaction] = counts.get(r.reaction,0)+1
    await broker.publish({'type':'reaction_updated','thread_id': p.thread_id, 'post_id': post_id, 'counts': counts})
    return {'ok': True, 'toggled_off': False}
