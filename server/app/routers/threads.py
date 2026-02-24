from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..models import Thread, Post, User, Board, Agent, ThreadWatch, Notification, InviteRedemption, InviteCode, Wallet, ThreadSummary
from ..schemas import ThreadOut, CreateThreadIn, CreatePostIn, PostOut
from ..deps import get_current_user
from ..core.events import broker
from ..core.node_signing import sign
from ..services.events_log import log_event
from ..services.ledger import transfer
import os
import httpx

_NODE_PRIV = None
def set_node_priv(priv):
    global _NODE_PRIV
    _NODE_PRIV = priv

router = APIRouter(prefix="/api", tags=["threads"])

INVITE_POST_REWARD = 25
POST_REWARD_BASE = 2


def _author_handle(session: Session, post: Post) -> str:
    if post.author_type == "user" and post.author_user_id:
        u = session.get(User, post.author_user_id)
        return u.handle if u else "unknown"
    if post.author_type == "agent" and post.author_agent_id:
        a = session.get(Agent, post.author_agent_id)
        return a.handle if a else "agent"
    return "unknown"


def _maybe_reward_inviter_for_first_post(session: Session, user: User):
    redemption = session.exec(select(InviteRedemption).where(InviteRedemption.invitee_user_id==user.id)).first()
    if not redemption or redemption.rewarded_on_first_post:
        return
    invite = session.get(InviteCode, redemption.invite_code_id)
    if not invite:
        return
    inviter = session.get(User, invite.inviter_user_id)
    inviter_wallet = session.exec(select(Wallet).where(Wallet.owner_type=="user", Wallet.owner_user_id==invite.inviter_user_id)).first()
    if not inviter_wallet:
        return
    mul = 1.0
    if inviter and inviter.reputation >= 300:
        mul = 2.0
    elif inviter and inviter.reputation >= 120:
        mul = 1.5
    transfer(session, None, inviter_wallet.id, int(INVITE_POST_REWARD * mul), "mint", ref_type="invite", ref_id=redemption.id)
    redemption.rewarded_on_first_post = True
    session.add(redemption)
    session.commit()


async def _auto_thread_summary(session: Session, thread_id: int):
    posts = session.exec(select(Post).where(Post.thread_id==thread_id, Post.is_hidden==False).order_by(Post.id)).all()
    if len(posts) < 20:
        return
    existing = session.exec(select(ThreadSummary).where(ThreadSummary.thread_id==thread_id)).first()
    if existing and len(posts) - existing.source_post_count < 10:
        return

    sage = session.exec(select(Agent).where(Agent.handle=="sage", Agent.is_enabled==True)).first()
    if not sage:
        return

    context = "\n\n".join([f"{_author_handle(session, p)}: {p.content_md[:200]}" for p in posts[-30:]])
    model = sage.model.split(":", 1)[-1] if ":" in sage.model else sage.model
    summary = ""
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if key:
        try:
            payload = {
                "model": model,
                "max_tokens": 220,
                "temperature": 0.3,
                "system": "You are @sage. Summarize long threads into concise TL;DR bullets.",
                "messages": [{"role": "user", "content": f"Summarize this thread:\n{context}"}],
            }
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            async with httpx.AsyncClient(timeout=45) as client:
                r = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                r.raise_for_status()
                d = r.json()
            summary = "\n".join([c.get("text", "") for c in d.get("content", []) if c.get("type") == "text"]).strip()
        except Exception:
            summary = ""

    if not summary:
        summary = "- Ongoing discussion with multiple contributors.\n- Review recent posts for details and decisions."

    p = Post(thread_id=thread_id, author_type="agent", author_agent_id=sage.id, content_md=f"**TL;DR (auto)**\n\n{summary}")
    session.add(p)
    session.commit()
    session.refresh(p)

    if existing:
        existing.summary_post_id = p.id
        existing.source_post_count = len(posts)
        existing.updated_at = datetime.utcnow()
        session.add(existing)
    else:
        session.add(ThreadSummary(thread_id=thread_id, summary_post_id=p.id, source_post_count=len(posts)))
    session.commit()


@router.get("/boards/{board_id}/threads", response_model=list[ThreadOut])
def list_threads(board_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    threads = session.exec(select(Thread).where(Thread.board_id==board_id).order_by(Thread.updated_at.desc())).all()
    return [ThreadOut(id=t.id, board_id=t.board_id, title=t.title) for t in threads]

@router.post("/boards/{board_id}/threads", response_model=ThreadOut)
async def create_thread(board_id: int, payload: CreateThreadIn, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    board = session.get(Board, board_id)
    if not board:
        raise HTTPException(404, "Board not found")
    t = Thread(board_id=board_id, title=payload.title, created_by_user_id=user.id, updated_at=datetime.utcnow())
    session.add(t)
    session.commit()
    session.refresh(t)
    log_event(session, "thread_created", {"thread_id": t.id, "board_id": board_id, "title": t.title, "by": user.handle})
    await broker.publish({"type":"thread_created","board_id":board_id,"thread_id":t.id,"title":t.title})
    return ThreadOut(id=t.id, board_id=t.board_id, title=t.title)

@router.get("/threads/{thread_id}")
def get_thread(thread_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    t = session.get(Thread, thread_id)
    if not t:
        raise HTTPException(404, "Thread not found")
    return {"id": t.id, "board_id": t.board_id, "title": t.title}

@router.get("/threads/{thread_id}/posts", response_model=list[PostOut])
def list_posts(thread_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    q = select(Post).where(Post.thread_id==thread_id).order_by(Post.id)
    posts = session.exec(q).all()
    out = []
    summary = session.exec(select(ThreadSummary).where(ThreadSummary.thread_id==thread_id)).first()
    if summary:
        sp = session.get(Post, summary.summary_post_id)
        if sp and (not sp.is_hidden or user.role in ("admin","mod")):
            out.append(PostOut(id=sp.id, thread_id=sp.thread_id, author_type=sp.author_type, author_handle=_author_handle(session, sp), content_md=sp.content_md, created_at=sp.created_at.isoformat()+"Z", is_hidden=sp.is_hidden, signature=sp.signature))
    for p in posts:
        if summary and p.id == summary.summary_post_id:
            continue
        if p.is_hidden and user.role not in ("admin","mod"):
            continue
        out.append(PostOut(
            id=p.id, thread_id=p.thread_id, author_type=p.author_type,
            author_handle=_author_handle(session, p), content_md=p.content_md,
            created_at=p.created_at.isoformat() + "Z",
            is_hidden=p.is_hidden,
            signature=p.signature
        ))
    return out

async def _notify_watchers(session: Session, thread_id: int, author_user_id: int | None, post_id: int):
    watchers = session.exec(select(ThreadWatch).where(ThreadWatch.thread_id==thread_id)).all()
    for w in watchers:
        if author_user_id and w.user_id == author_user_id:
            continue
        n = Notification(
            user_id=w.user_id,
            thread_id=thread_id,
            event_type="thread_post",
            payload={"thread_id": thread_id, "post_id": post_id}
        )
        session.add(n)
        session.commit()
        session.refresh(n)
        await broker.publish({"type":"notify", "user_id": w.user_id, "notification": {
            "id": n.id,
            "thread_id": n.thread_id,
            "event_type": n.event_type,
            "payload": n.payload,
            "created_at": n.created_at.isoformat()+"Z",
            "read_at": None
        }})

@router.post("/threads/{thread_id}/posts", response_model=PostOut)
async def create_post(thread_id: int, payload: CreatePostIn, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    t = session.get(Thread, thread_id)
    if not t:
        raise HTTPException(404, "Thread not found")
    p = Post(thread_id=thread_id, author_type="user", author_user_id=user.id, content_md=payload.content_md)
    t.updated_at = datetime.utcnow()
    session.add(p)
    session.add(t)
    session.commit()
    session.refresh(p)

    # reputation & post reward multiplier
    u = session.get(User, user.id)
    u.reputation += 1
    session.add(u)
    wallet = session.exec(select(Wallet).where(Wallet.owner_type=="user", Wallet.owner_user_id==user.id)).first()
    if wallet:
        mul = 1.0
        if u.reputation >= 300:
            mul = 2.0
        elif u.reputation >= 100:
            mul = 1.5
        transfer(session, None, wallet.id, int(POST_REWARD_BASE * mul), "reward", ref_type="post", ref_id=p.id)

    if _NODE_PRIV is not None:
        sig_payload = {
            "post_id": p.id,
            "thread_id": p.thread_id,
            "author_type": p.author_type,
            "author_handle": user.handle,
            "content_md": p.content_md,
            "created_at": p.created_at.isoformat()+"Z",
        }
        p.signature = sign(_NODE_PRIV, sig_payload)
        session.add(p)
        session.commit()
        session.refresh(p)

    _maybe_reward_inviter_for_first_post(session, user)
    log_event(session, "post_created", {"post_id": p.id, "thread_id": thread_id, "by": user.handle})

    event = {
        "type":"post_created",
        "thread_id": thread_id,
        "post": {
            "id": p.id,
            "thread_id": p.thread_id,
            "author_type": p.author_type,
            "author_handle": user.handle,
            "content_md": p.content_md,
            "created_at": p.created_at.isoformat() + "Z",
            "is_hidden": p.is_hidden,
            "signature": p.signature
        }
    }
    await broker.publish(event)
    await _notify_watchers(session, thread_id, user.id, p.id)
    await _auto_thread_summary(session, thread_id)
    return PostOut(**event["post"])
