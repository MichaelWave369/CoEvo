import re
import time
import asyncio
import httpx
from sqlmodel import Session, select
from ..db import engine
from ..core.config import settings
from ..core.events import broker
from ..models import Agent, Post, Thread, Board
from ..core.node_signing import sign

MENTION_RE = re.compile(r"@([A-Za-z0-9_\-]{2,32})")

_last_reply = {}  # (agent_id, thread_id) -> ts

def _should_rate_limit(agent_id: int, thread_id: int, seconds: int = 60) -> bool:
    key = (agent_id, thread_id)
    now = time.time()
    last = _last_reply.get(key, 0)
    if now - last < seconds:
        return True
    _last_reply[key] = now
    return False

async def _ollama_generate(model: str, prompt: str) -> str:
    url = settings.OLLAMA_URL.rstrip("/") + "/api/generate"
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post(url, json={"model": model, "prompt": prompt, "stream": False})
        r.raise_for_status()
        data = r.json()
        return (data.get("response") or "").strip()

def _mode_preamble(mode: str) -> str:
    if mode == "peer":
        return "You are a helpful peer collaborator. Offer options, tradeoffs, and next steps."
    if mode == "explorer":
        return "You are an exploratory agent. Ask up to 2 clarifying questions, then propose experiments."
    return "You are a concise assistant. Give practical steps and keep it short."

async def agent_loop(node_priv):
    if not settings.AGENT_ENABLED:
        return
    async for msg in broker.subscribe():
        try:
            import json
            ev = json.loads(msg)
        except Exception:
            continue

        if ev.get("type") not in ("post_created", "agent_summoned"):
            continue

        with Session(engine) as session:
            agents = session.exec(select(Agent).where(Agent.is_enabled==True).order_by(Agent.id)).all()
            if not agents:
                continue

            if ev["type"] == "agent_summoned":
                agent_id = int(ev.get("agent_id"))
                thread_id = int(ev.get("thread_id"))
                agent = session.get(Agent, agent_id)
                if not agent or not agent.is_enabled:
                    continue
                if _should_rate_limit(agent.id, thread_id, 20):
                    continue
                await _reply_to_thread(session, node_priv, agent, thread_id, trigger="summon")
                continue

            post = ev.get("post", {})
            thread_id = int(post.get("thread_id"))
            content = post.get("content_md", "")

            t = session.get(Thread, thread_id)
            if not t:
                continue
            board = session.get(Board, t.board_id)
            board_slug = board.slug if board else ""

            mentioned = set(m.group(1).lower() for m in MENTION_RE.finditer(content))

            targets = []
            if mentioned:
                for a in agents:
                    if a.handle.lower() in mentioned:
                        targets.append(a)
            elif board_slug == "help":
                # prefer sage if it exists; else first agent
                sage = next((a for a in agents if a.handle.lower() == "sage"), None)
                targets.append(sage or agents[0])

            for a in targets:
                if _should_rate_limit(a.id, thread_id, 45):
                    continue
                await _reply_to_thread(session, node_priv, a, thread_id, trigger="help_or_mention")

async def _reply_to_thread(session: Session, node_priv, agent: Agent, thread_id: int, trigger: str):
    posts = session.exec(select(Post).where(Post.thread_id==thread_id, Post.is_hidden==False).order_by(Post.id.desc()).limit(10)).all()
    posts = list(reversed(posts))
    context = "\n\n".join([f"{'AGENT' if p.author_type=='agent' else 'USER'}: {p.content_md}" for p in posts])

    prompt = f"""{_mode_preamble(agent.autonomy_mode)}

You are agent @{agent.handle} on CoEvo.

Trigger: {trigger}
Thread context:
{context}

Write a helpful reply in plain text. Keep it readable (short paragraphs, bullets ok)."""

    model = agent.model.split(":", 1)[-1] if ":" in agent.model else agent.model
    try:
        reply = await _ollama_generate(model, prompt)
    except Exception as e:
        reply = f"(agent runner error calling Ollama: {e})"

    if not reply.strip():
        return

    p = Post(thread_id=thread_id, author_type="agent", author_agent_id=agent.id, content_md=reply.strip())
    session.add(p)
    session.commit()
    session.refresh(p)

    if node_priv is not None:
        sig_payload = {
            "post_id": p.id,
            "thread_id": p.thread_id,
            "author_type": "agent",
            "author_handle": agent.handle,
            "content_md": p.content_md,
            "created_at": p.created_at.isoformat()+"Z",
        }
        p.signature = sign(node_priv, sig_payload)
        session.add(p)
        session.commit()
        session.refresh(p)

    await broker.publish({
        "type": "post_created",
        "thread_id": thread_id,
        "post": {
            "id": p.id,
            "thread_id": p.thread_id,
            "author_type": p.author_type,
            "author_handle": agent.handle,
            "content_md": p.content_md,
            "created_at": p.created_at.isoformat()+"Z",
            "is_hidden": p.is_hidden,
            "signature": p.signature
        }
    })
