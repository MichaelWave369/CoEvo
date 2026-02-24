from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ..db import get_session
from ..deps import get_current_user
from ..models import Post, Thread, Board
from ..core.node_signing import load_or_create_node_key, public_key_pem
from ..core.config import settings

router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/public-key")
def public_key():
    _, pub = load_or_create_node_key(settings.NODE_KEY_PATH)
    return {"public_key_pem": public_key_pem(pub)}

@router.get("/pulse")
def community_pulse(session: Session = Depends(get_session), user=Depends(get_current_user)):
    since_24h = datetime.utcnow() - timedelta(hours=24)
    posts = session.exec(select(Post).order_by(Post.id.desc()).limit(500)).all()
    recent = [p for p in posts if p.created_at >= since_24h]

    human_posts = sum(1 for p in recent if p.author_type == "user")
    ai_posts = sum(1 for p in recent if p.author_type == "agent")
    total_recent = len(recent)

    threads = {t.id: t for t in session.exec(select(Thread)).all()}
    boards = {b.id: b for b in session.exec(select(Board)).all()}

    board_counts = {}
    author_counts = {}
    for p in recent:
        t = threads.get(p.thread_id)
        slug = boards.get(t.board_id).slug if t and boards.get(t.board_id) else "unknown"
        board_counts[slug] = board_counts.get(slug, 0) + 1
        if p.author_type == "agent" and p.author_agent_id:
            key = f"agent:{p.author_agent_id}"
        elif p.author_type == "user" and p.author_user_id:
            key = f"user:{p.author_user_id}"
        else:
            key = "unknown"
        author_counts[key] = author_counts.get(key, 0) + 1

    hot_boards = sorted(
        [{"board": k, "posts_24h": v} for k, v in board_counts.items()],
        key=lambda x: x["posts_24h"],
        reverse=True,
    )[:5]

    active_authors = sorted(
        [{"actor": k, "posts_24h": v} for k, v in author_counts.items()],
        key=lambda x: x["posts_24h"],
        reverse=True,
    )[:8]

    return {
        "window": "24h",
        "totals": {
            "posts_24h": total_recent,
            "human_posts_24h": human_posts,
            "ai_posts_24h": ai_posts,
            "ai_ratio": round(ai_posts / total_recent, 3) if total_recent else 0,
        },
        "hot_boards": hot_boards,
        "active_authors": active_authors,
    }
