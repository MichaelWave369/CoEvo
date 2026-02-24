from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..deps import get_current_user
from ..models import User, Agent, Post, Bounty
from ..schemas import UpdateBioIn

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

@router.get('/user/{handle}')
def user_profile(handle: str, session: Session = Depends(get_session)):
    u = session.exec(select(User).where(User.handle==handle)).first()
    if not u:
        raise HTTPException(404, 'Not found')
    posts = session.exec(select(Post).where(Post.author_type=='user', Post.author_user_id==u.id).order_by(Post.id.desc()).limit(50)).all()
    bounties_done = session.exec(select(Bounty).where(Bounty.claimed_by_user_id==u.id, Bounty.status=='paid')).all()
    return {
        'type': 'user', 'handle': u.handle, 'bio': u.bio, 'reputation': u.reputation,
        'bounties_completed': len(bounties_done),
        'posts': [{"id":p.id,"thread_id":p.thread_id,"content_md":p.content_md,"created_at":p.created_at.isoformat()+"Z"} for p in posts]
    }

@router.get('/agent/{handle}')
def agent_profile(handle: str, session: Session = Depends(get_session)):
    a = session.exec(select(Agent).where(Agent.handle==handle)).first()
    if not a:
        raise HTTPException(404, 'Not found')
    posts = session.exec(select(Post).where(Post.author_type=='agent', Post.author_agent_id==a.id).order_by(Post.id.desc()).limit(50)).all()
    return {
        'type':'agent', 'handle':a.handle, 'bio':a.bio, 'reputation':a.reputation,
        'bounties_completed': 0,
        'posts': [{"id":p.id,"thread_id":p.thread_id,"content_md":p.content_md,"created_at":p.created_at.isoformat()+"Z"} for p in posts]
    }

@router.patch('/me/bio')
def update_my_bio(payload: UpdateBioIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    u = session.get(User, user.id)
    u.bio = payload.bio[:400]
    session.add(u)
    session.commit()
    return {'ok': True, 'bio': u.bio}
