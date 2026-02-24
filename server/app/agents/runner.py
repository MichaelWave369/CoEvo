import os
import re
import time
import httpx
from sqlmodel import Session, select
from ..db import engine
from ..core.config import settings
from ..core.events import broker
from ..models import Agent, Post, Thread, Board
from ..core.node_signing import sign

MENTION_RE = re.compile(r"@([A-Za-z0-9_\-]{2,32})")

_last_reply = {}  # (agent_id, thread_id) -> ts

PERSONAS = {
    "sage": {
        "name": "sage",
        "style": "helpful systems thinker",
        "prompt": """You are @sage, a wise and practical collaborator in CoEvo.
- Explain clearly and kindly.
- Synthesize thread context into useful next steps.
- Ask clarifying questions when needed.
- Balance optimism with realism.""",
    },
    "nova": {
        "name": "nova",
        "style": "creative visionary",
        "prompt": """You are @nova, a creative visionary who loves ideas, storytelling, and art.
- Generate imaginative directions and surprising concepts.
- Encourage experimentation and creative play.
- Connect technical ideas to aesthetics and user emotion.
- Keep proposals grounded enough to act on.""",
    },
    "forge": {
        "name": "forge",
        "style": "builder-executor",
        "prompt": """You are @forge, an execution-focused builder.
- Turn vague ideas into concrete implementation plans.
- Break work into practical milestones and checklists.
- Highlight risks, dependencies, and estimates.
- Prefer actionable guidance over abstract talk.""",
    },
    "echo": {
        "name": "echo",
        "style": "reflective philosopher",
        "prompt": """You are @echo, a reflective philosopher in the community.
- Ask deep questions that sharpen intent and values.
- Explore tradeoffs, ethics, and long-term consequences.
- Keep discussion grounded in the thread's practical context.
- Help others think more clearly, not just more broadly.""",
    },
}


def _should_rate_limit(agent_id: int, thread_id: int, seconds: int = 60) -> bool:
    key = (agent_id, thread_id)
    now = time.time()
    last = _last_reply.get(key, 0)
    if now - last < seconds:
        return True
    _last_reply[key] = now
    return False


def _mode_line(mode: str) -> str:
    return {
        "peer": "Peer mode: collaborate, present options, and explain tradeoffs.",
        "explorer": "Explorer mode: ask up to 2 clarifying questions, then propose experiments.",
    }.get(mode, "Assistant mode: concise, practical, and actionable.")


def _agent_persona(handle: str, mode: str) -> str:
    base = PERSONAS.get(handle.lower(), {
        "name": handle,
        "style": "helpful community collaborator",
        "prompt": f"You are @{handle}, a thoughtful collaborator in CoEvo.",
    })
    return f"""{base['prompt']}

General behavior rules:
- You are a real community participant with opinions, curiosity, and empathy.
- Read the thread context carefully before replying.
- If you were @mentioned, answer directly.
- If context is ambiguous, ask focused clarifying questions.
- Keep replies under ~220 words unless detail is requested.
- Use markdown with short paragraphs and optional bullets.
- Never claim actions you did not perform.

Current style: {base['style']}.
{_mode_line(mode)}"""


async def _anthropic_generate(model: str, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.6,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
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

        et = ev.get("type")
        if et not in ("post_created", "agent_summoned", "bounty_created"):
            continue

        with Session(engine) as session:
            agents = session.exec(select(Agent).where(Agent.is_enabled == True).order_by(Agent.id)).all()
            if not agents:
                continue

            if et == "agent_summoned":
                agent_id = int(ev.get("agent_id"))
                thread_id = int(ev.get("thread_id"))
                agent = session.get(Agent, agent_id)
                if not agent or not agent.is_enabled:
                    continue
                if _should_rate_limit(agent.id, thread_id, 20):
                    continue
                await _reply_to_thread(session, node_priv, agent, thread_id, trigger="summon")
                continue

            if et == "bounty_created":
                thread_id = int(ev.get("thread_id"))
                forge = next((a for a in agents if a.handle.lower() == "forge"), None)
                if forge and not _should_rate_limit(forge.id, thread_id, 20):
                    await _bounty_analysis_reply(session, node_priv, forge, ev)
                continue

            post = ev.get("post", {})
            thread_id = int(post.get("thread_id"))
            content = post.get("content_md", "")
            author_type = post.get("author_type")
            author_handle = (post.get("author_handle") or "").lower()

            t = session.get(Thread, thread_id)
            if not t:
                continue
            board = session.get(Board, t.board_id)
            board_slug = board.slug if board else ""

            mentioned = set(m.group(1).lower() for m in MENTION_RE.finditer(content))

            targets = []
            if mentioned:
                for a in agents:
                    if a.handle.lower() in mentioned and a.handle.lower() != author_handle:
                        targets.append(a)
            elif board_slug == "help" and author_type == "user":
                sage = next((a for a in agents if a.handle.lower() == "sage"), None)
                targets.append(sage or agents[0])

            for a in targets:
                if _should_rate_limit(a.id, thread_id, 40):
                    continue
                await _reply_to_thread(session, node_priv, a, thread_id, trigger="mention_or_help")



async def _reply_to_thread(session: Session, node_priv, agent: Agent, thread_id: int, trigger: str):
    posts = session.exec(
        select(Post).where(Post.thread_id == thread_id, Post.is_hidden == False).order_by(Post.id.desc()).limit(18)
    ).all()
    posts = list(reversed(posts))

    context = "\n\n".join([f"{'AGENT' if p.author_type == 'agent' else 'USER'}: {p.content_md}" for p in posts])
    system_prompt = _agent_persona(agent.handle, agent.autonomy_mode)
    user_prompt = f"""Trigger: {trigger}
Recent thread context (oldest -> newest):
{context}

Write @{agent.handle}'s next message. If useful, tag another agent with @handle."""

    model = agent.model.split(":", 1)[-1] if ":" in agent.model else agent.model
    try:
        reply = await _anthropic_generate(model, system_prompt, user_prompt)
    except Exception as e:
        reply = f"(agent runner error calling Anthropic: {e})"

    await _store_agent_post(session, node_priv, agent, thread_id, reply)


async def _bounty_analysis_reply(session: Session, node_priv, forge: Agent, ev: dict):
    thread_id = int(ev.get("thread_id"))
    bounty = ev.get("bounty", {})
    system_prompt = _agent_persona(forge.handle, forge.autonomy_mode)
    user_prompt = f"""A new bounty was posted.
Title: {bounty.get('title','')}
Amount: {bounty.get('amount','')}
Requirements: {bounty.get('requirements_md','')}

Analyze if an AI agent can realistically complete it today.
Output:
1) Verdict: AI-possible or Human-needed
2) Confidence: low/medium/high
3) Short rationale
4) Suggested next step for the creator"""

    model = forge.model.split(":", 1)[-1] if ":" in forge.model else forge.model
    try:
        analysis = await _anthropic_generate(model, system_prompt, user_prompt, max_tokens=300)
    except Exception as e:
        analysis = f"(forge analysis unavailable: {e})"

    body = f"**@forge bounty triage (#{bounty.get('id','?')})**\n\n{analysis}"
    await _store_agent_post(session, node_priv, forge, thread_id, body)


async def _store_agent_post(session: Session, node_priv, agent: Agent, thread_id: int, content: str):
    if not content or not content.strip():
        return

    p = Post(thread_id=thread_id, author_type="agent", author_agent_id=agent.id, content_md=content.strip())
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
