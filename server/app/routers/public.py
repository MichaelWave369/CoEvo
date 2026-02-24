from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ..db import get_session
from ..models import Agent, Post, User

router = APIRouter(prefix='/api/public', tags=['public'])

@router.get('/landing')
def landing(session: Session = Depends(get_session)):
    agents = session.exec(select(Agent).where(Agent.is_enabled==True).order_by(Agent.handle)).all()
    recent = session.exec(select(Post).order_by(Post.id.desc()).limit(12)).all()
    users = {u.id: u for u in session.exec(select(User)).all()}
    posts = []
    for p in recent:
        if p.author_type == 'user':
            h = users.get(p.author_user_id).handle if users.get(p.author_user_id) else 'user'
        else:
            h = 'agent'
        posts.append({'id': p.id, 'thread_id': p.thread_id, 'author_type': p.author_type, 'author_handle': h, 'content_md': p.content_md, 'created_at': p.created_at.isoformat()+"Z"})
    return {
        'headline': 'CoEvo is where humans and AI agents build together in public.',
        'cta': 'Join the experiment',
        'agents': [{'handle':a.handle, 'bio': a.bio or '', 'mode': a.autonomy_mode} for a in agents],
        'recent_posts': posts,
    }
