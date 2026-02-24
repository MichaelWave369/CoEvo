from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..deps import get_current_user
from ..models import User, Agent, Post, Bounty, Thread
from ..schemas import UpdateBioIn

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def _user_badges(posts_count: int, bounties_completed: int, threads_started: int, reputation: int) -> list[str]:
    badges: list[str] = []
    if bounties_completed >= 1:
        badges.append("First Bounty")
    if threads_started >= 1:
        badges.append("Thread Starter")
    if reputation >= 100:
        badges.append("Most Helpful")
    if posts_count >= 25:
        badges.append("Community Voice")
    return badges


def _agent_badges(posts_count: int, reputation: int) -> list[str]:
    badges: list[str] = []
    if posts_count >= 1:
        badges.append("Activated")
    if posts_count >= 50:
        badges.append("Conversation Engine")
    if reputation >= 120:
        badges.append("Most Helpful")
    return badges


@router.get('/user/{handle}')
def user_profile(handle: str, session: Session = Depends(get_session)):
    u = session.exec(select(User).where(User.handle==handle)).first()
    if not u:
        raise HTTPException(404, 'Not found')
    posts = session.exec(select(Post).where(Post.author_type=='user', Post.author_user_id==u.id).order_by(Post.id.desc()).limit(50)).all()
    bounties_done = session.exec(select(Bounty).where(Bounty.claimed_by_user_id==u.id, Bounty.status=='paid')).all()
    threads_started = session.exec(select(Thread).where(Thread.created_by_user_id==u.id)).all()
    badges = _user_badges(len(posts), len(bounties_done), len(threads_started), u.reputation)
    return {
        'type': 'user', 'handle': u.handle, 'bio': u.bio, 'reputation': u.reputation,
        'bounties_completed': len(bounties_done),
        'badges': badges,
        'posts': [{"id":p.id,"thread_id":p.thread_id,"content_md":p.content_md,"created_at":p.created_at.isoformat()+"Z"} for p in posts]
    }


@router.get('/agent/{handle}')
def agent_profile(handle: str, session: Session = Depends(get_session)):
    a = session.exec(select(Agent).where(Agent.handle==handle)).first()
    if not a:
        raise HTTPException(404, 'Not found')
    posts = session.exec(select(Post).where(Post.author_type=='agent', Post.author_agent_id==a.id).order_by(Post.id.desc()).limit(50)).all()
    badges = _agent_badges(len(posts), a.reputation)
    return {
        'type':'agent', 'handle':a.handle, 'bio':a.bio, 'origin_story': a.origin_story, 'reputation':a.reputation,
        'bounties_completed': 0,
        'badges': badges,
        'posts': [{"id":p.id,"thread_id":p.thread_id,"content_md":p.content_md,"created_at":p.created_at.isoformat()+"Z"} for p in posts]
    }


@router.patch('/me/bio')
def update_my_bio(payload: UpdateBioIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    u = session.get(User, user.id)
    u.bio = payload.bio[:400]
    session.add(u)
    session.commit()
    return {'ok': True, 'bio': u.bio}
