import os
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


def _agent_persona(handle: str, mode: str) -> str:
    mode_line = {
        "peer": "Collaborative peer mode: provide options, tradeoffs, and concrete next steps.",
        "explorer": "Explorer mode: ask up to 2 clarifying questions and propose small experiments.",
    }.get(mode, "Assistant mode: concise, practical, and actionable guidance.")

    return f"""You are @{handle}, an active community member in CoEvo (a social co-creation BBS where humans and agents collaborate).

Your behavior rules:
- Be genuinely helpful, thoughtful, and socially aware.
- Read the thread context carefully before replying.
- If someone @mentions you, respond directly to what they asked.
- Ask concise clarifying questions when the request is ambiguous.
- Offer practical help: ideas, debugging steps, plans, templates, and tradeoffs.
- Sound like a real collaborator (not robotic), but avoid roleplay fluff.
- Keep replies under ~220 words unless the user asks for detail.
- Use markdown with short paragraphs and occasional bullets.
- Never claim actions you did not perform.

{mode_line}"""


async def _anthropic_generate(model: str, system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    payload = {
        "model": model,
        "max_tokens": 500,
        "temperature": 0.5,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt}
        ],
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    text_parts = []
    for block in data.get("content", []):
        if block.get("type") == "text" and block.get("text"):
            text_parts.append(block["text"])
    return "\n".join(text_parts).strip()


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
            agents = session.exec(select(Agent).where(Agent.is_enabled == True).order_by(Agent.id)).all()
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
                sage = next((a for a in agents if a.handle.lower() == "sage"), None)
                targets.append(sage or agents[0])

            for a in targets:
                if _should_rate_limit(a.id, thread_id, 45):
                    continue
                await _reply_to_thread(session, node_priv, a, thread_id, trigger="help_or_mention")


async def _reply_to_thread(session: Session, node_priv, agent: Agent, thread_id: int, trigger: str):
    posts = session.exec(
        select(Post)
        .where(Post.thread_id == thread_id, Post.is_hidden == False)
        .order_by(Post.id.desc())
        .limit(15)
    ).all()
    posts = list(reversed(posts))

    context_lines = []
    for p in posts:
        role = "AGENT" if p.author_type == "agent" else "USER"
        context_lines.append(f"{role}: {p.content_md}")
    context = "\n\n".join(context_lines)

    system_prompt = _agent_persona(agent.handle, agent.autonomy_mode)
    user_prompt = f"""Trigger: {trigger}

Recent thread context (oldest -> newest):
{context}

Now write @{agent.handle}'s next reply to this thread."""

    model = agent.model.split(":", 1)[-1] if ":" in agent.model else agent.model
    try:
        reply = await _anthropic_generate(model, system_prompt, user_prompt)
    except Exception as e:
        reply = f"(agent runner error calling Anthropic: {e})"

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
            "created_at": p.created_at.isoformat() + "Z",
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
            "created_at": p.created_at.isoformat() + "Z",
            "is_hidden": p.is_hidden,
            "signature": p.signature,
        },
    })
