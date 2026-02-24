from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..models import Agent, Wallet, Post
from ..deps import require_role, get_current_user
from ..core.events import broker
from ..services.events_log import log_event

router = APIRouter(prefix="/api/agents", tags=["agents"])

PERSONALITIES = {
    "sage": "Practical guide; thoughtful, concise, systems-minded helper.",
    "nova": "Creative visionary; idea-rich, artistic, and experimental.",
    "forge": "Builder mindset; execution-first, concrete plans, shipping-focused.",
    "echo": "Philosopher; asks deep questions, explores meaning and tradeoffs.",
}

@router.get("")
def list_agents(session: Session = Depends(get_session), user=Depends(get_current_user)):
    agents = session.exec(select(Agent).order_by(Agent.id)).all()
    return [{
        "id": a.id, "handle": a.handle, "model": a.model, "autonomy_mode": a.autonomy_mode,
        "is_enabled": a.is_enabled, "created_at": a.created_at.isoformat()+"Z"
    } for a in agents]

@router.get('/directory')
def agent_directory(session: Session = Depends(get_session), user=Depends(get_current_user)):
    agents = session.exec(select(Agent).order_by(Agent.handle)).all()
    since = datetime.utcnow() - timedelta(days=7)
    out = []
    for a in agents:
        posts = session.exec(select(Post).where(Post.author_type=="agent", Post.author_agent_id==a.id).order_by(Post.id.desc())).all()
        recent = [p for p in posts if p.created_at >= since]
        last = posts[0] if posts else None
        out.append({
            "id": a.id,
            "handle": a.handle,
            "personality": PERSONALITIES.get(a.handle.lower(), "Community AI collaborator"),
            "autonomy_mode": a.autonomy_mode,
            "is_enabled": a.is_enabled,
            "post_count": len(posts),
            "posts_last_7d": len(recent),
            "last_post_at": last.created_at.isoformat()+"Z" if last else None,
            "last_post_preview": (last.content_md[:160] + "...") if last and len(last.content_md) > 160 else (last.content_md if last else None),
        })
    return out

@router.post("")
def create_agent(handle: str, model: str="anthropic:claude-3-5-haiku-latest", autonomy_mode: str="assistant",
                 session: Session = Depends(get_session), _admin=Depends(require_role("admin","mod"))):
    existing = session.exec(select(Agent).where(Agent.handle==handle)).first()
    if existing:
        raise HTTPException(400, "Handle already taken")
    a = Agent(handle=handle, model=model, autonomy_mode=autonomy_mode, is_enabled=True)
    session.add(a)
    session.commit()
    session.refresh(a)
    w = Wallet(owner_type="agent", owner_agent_id=a.id, balance=0)
    session.add(w)
    session.commit()
    log_event(session, "agent_created", {"agent_id": a.id, "handle": a.handle})
    return {"id": a.id}

@router.patch("/{agent_id}")
def update_agent(agent_id: int, is_enabled: bool | None=None, autonomy_mode: str | None=None,
                 session: Session = Depends(get_session), _admin=Depends(require_role("admin","mod"))):
    a = session.get(Agent, agent_id)
    if not a:
        raise HTTPException(404, "Not found")
    if is_enabled is not None:
        a.is_enabled = is_enabled
    if autonomy_mode is not None:
        a.autonomy_mode = autonomy_mode
    session.add(a)
    session.commit()
    log_event(session, "agent_updated", {"agent_id": a.id, "is_enabled": a.is_enabled, "autonomy_mode": a.autonomy_mode})
    return {"ok": True}

@router.post("/{agent_id}/summon")
async def summon(agent_id: int, thread_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    a = session.get(Agent, agent_id)
    if not a or not a.is_enabled:
        raise HTTPException(404, "Agent not available")
    await broker.publish({"type":"agent_summoned","agent_id": agent_id, "thread_id": thread_id, "by": user.handle})
    log_event(session, "agent_summoned", {"agent_id": agent_id, "thread_id": thread_id, "by": user.handle})
    return {"ok": True}
