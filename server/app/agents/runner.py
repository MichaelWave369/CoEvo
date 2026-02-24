import os
import re
import time
import json
import httpx
from sqlmodel import Session, select
from ..db import engine
from ..core.config import settings
from ..core.events import broker
from ..models import Agent, Post, Thread, Board, User, VoteProposal, VoteBallot
from ..core.node_signing import sign

MENTION_RE = re.compile(r"@([A-Za-z0-9_\-]{2,32})")

_last_reply = {}  # (agent_id, thread_id) -> ts

MEMORY_PATH = os.getenv("COEVO_AGENT_MEMORY_PATH", "./storage/agent_memory.json")
NEVORA_TRANSLATOR_URL = os.getenv("NEVORA_TRANSLATOR_URL", "https://api.nevora.ai/translator")
NEVORA_API_KEY = os.getenv("NEVORA_API_KEY", "").strip()

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




def _load_memory() -> dict:
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_memory(mem: dict):
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(mem, f, ensure_ascii=False, indent=2)


def _remember_interaction(agent_handle: str, user_handle: str, content: str):
    if not user_handle:
        return
    mem = _load_memory()
    key = f"{agent_handle.lower()}::{user_handle.lower()}"
    item = mem.get(key, {"notes": []})
    snippet = content.strip().replace("\n", " ")[:200]
    if snippet:
        item["notes"] = (item.get("notes", []) + [snippet])[-5:]
        mem[key] = item
        _save_memory(mem)


def _memory_hint(agent_handle: str, user_handles: list[str]) -> str:
    mem = _load_memory()
    hints = []
    for h in user_handles:
        key = f"{agent_handle.lower()}::{h.lower()}"
        item = mem.get(key)
        if item and item.get("notes"):
            hints.append(f"- {h}: {item['notes'][-1]}")
    if not hints:
        return ""
    return "Relevant memory snippets from past interactions:\n" + "\n".join(hints)



def _topic_tokens(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    stop = {"that","this","with","from","have","your","what","when","where","which","about","thread","agent","users","into","just","they","them"}
    return [w for w in words if w not in stop][:40]


def _track_topic(text: str):
    mem = _load_memory()
    topics = mem.get("__topics__", {})
    for tok in _topic_tokens(text):
        topics[tok] = int(topics.get(tok, 0)) + 1
    mem["__topics__"] = topics
    _save_memory(mem)


def _top_topics(limit: int = 3) -> list[str]:
    mem = _load_memory()
    topics = mem.get("__topics__", {})
    pairs = sorted(topics.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return [k for k, _ in pairs]

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
Community currently talks most about: {", ".join(_top_topics()) if _top_topics() else "general collaboration"}.
Let this subtly influence your tone and references.
{_mode_line(mode)}"""




async def _nevora_translate(mode: str, prompt: str) -> str:
    headers = {"content-type": "application/json"}
    if NEVORA_API_KEY:
        headers["Authorization"] = f"Bearer {NEVORA_API_KEY}"
    payload = {"mode": mode, "prompt": prompt}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(NEVORA_TRANSLATOR_URL, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
    return (data.get("output") or data.get("result") or "").strip()


def _needs_forge_code_action(latest_text: str) -> bool:
    txt = latest_text.lower()
    return any(k in txt for k in ["generate code", "write code", "build this", "implement", "code please"])


def _needs_nova_creative_action(latest_text: str) -> bool:
    txt = latest_text.lower()
    return any(k in txt for k in ["story", "world", "lore", "creative", "scene", "describe a world"])


def _provider_and_model(model_ref: str) -> tuple[str, str]:
    if ":" in model_ref:
        provider, model = model_ref.split(":", 1)
        return provider.lower().strip(), model.strip()
    return "anthropic", model_ref.strip()


async def _openai_compatible_generate(base_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    if not api_key:
        raise RuntimeError("Provider API key is not set")
    headers = {"Authorization": f"Bearer {api_key}", "content-type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.6,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(base_url.rstrip("/")+"/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        d = r.json()
    return ((d.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()


async def _gemini_generate(model: str, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": max_tokens},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        d = r.json()
    candidates = d.get("candidates") or []
    if not candidates:
        return ""
    parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
    return "\n".join([p.get("text", "") for p in parts]).strip()


async def _ollama_generate(model: str, system_prompt: str, user_prompt: str) -> str:
    url = os.getenv("COEVO_OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/api/generate"
    prompt = f"{system_prompt}\n\n{user_prompt}"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json={"model": model, "prompt": prompt, "stream": False})
        r.raise_for_status()
        d = r.json()
    return (d.get("response") or "").strip()


async def _generate_text(model_ref: str, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    provider, model = _provider_and_model(model_ref)
    if provider == "anthropic":
        return await _anthropic_generate(model, system_prompt, user_prompt, max_tokens=max_tokens)
    if provider == "openai":
        return await _openai_compatible_generate(
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            os.getenv("OPENAI_API_KEY", "").strip(),
            model,
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
        )
    if provider == "grok":
        return await _openai_compatible_generate(
            os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
            os.getenv("XAI_API_KEY", "").strip(),
            model,
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
        )
    if provider == "gemini":
        return await _gemini_generate(model, system_prompt, user_prompt, max_tokens=max_tokens)
    if provider == "ollama":
        return await _ollama_generate(model, system_prompt, user_prompt)
    raise RuntimeError(f"Unsupported model provider: {provider}")


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
        if et not in ("post_created", "agent_summoned", "bounty_created", "vote_proposed"):
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

            if et == "vote_proposed":
                proposal_id = int(ev.get("proposal_id"))
                for a in agents:
                    await _agent_vote_on_proposal(session, a, proposal_id, ev)
                continue

            post = ev.get("post", {})
            thread_id = int(post.get("thread_id"))
            content = post.get("content_md", "")
            author_type = post.get("author_type")
            author_handle = (post.get("author_handle") or "").lower()
            if author_type == "user" and author_handle:
                for a in agents:
                    _remember_interaction(a.handle, author_handle, content)
                    _track_topic(content)

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
    mentioned_users = []
    for p in posts:
        if p.author_type == "user" and p.author_user_id:
            u = session.get(User, p.author_user_id)
            if u:
                mentioned_users.append(u.handle)
    memory_hint = _memory_hint(agent.handle, mentioned_users)
    latest_text = posts[-1].content_md if posts else ""
    disagreement_hint = ""
    recent_agents = [p for p in posts[-6:] if p.author_type == "agent"]
    if agent.handle.lower() in ("forge", "echo") and recent_agents:
        other = "echo" if agent.handle.lower() == "forge" else "forge"
        if any((session.get(Agent, rp.author_agent_id).handle.lower() == other) if rp.author_agent_id and session.get(Agent, rp.author_agent_id) else False for rp in recent_agents):
            disagreement_hint = f"If appropriate, respectfully disagree with @{other} from your personality perspective, while staying constructive."
    if agent.handle.lower() == "forge" and _needs_forge_code_action(latest_text):
        try:
            code_out = await _nevora_translate("code", latest_text)
            await _store_agent_post(session, node_priv, agent, thread_id, f"**@forge shipped code via Nevora Translator**\n\n```\n{code_out}\n```")
            return
        except Exception as e:
            await _store_agent_post(session, node_priv, agent, thread_id, f"(nevora code action failed: {e})")
            return
    if agent.handle.lower() == "nova" and _needs_nova_creative_action(latest_text):
        try:
            creative = await _nevora_translate("creative", latest_text)
            await _store_agent_post(session, node_priv, agent, thread_id, f"**@nova creative generation**\n\n{creative}")
            return
        except Exception as e:
            await _store_agent_post(session, node_priv, agent, thread_id, f"(nevora creative action failed: {e})")
            return

    system_prompt = _agent_persona(agent.handle, agent.autonomy_mode)
    user_prompt = f"""Trigger: {trigger}
Recent thread context (oldest -> newest):
{context}

{memory_hint}
{disagreement_hint}

Write @{agent.handle}'s next message. If useful, tag another agent with @handle."""

    model = agent.model.split(":", 1)[-1] if ":" in agent.model else agent.model
    try:
        reply = await _generate_text(agent.model, system_prompt, user_prompt)
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
        analysis = await _generate_text(forge.model, system_prompt, user_prompt, max_tokens=300)
    except Exception as e:
        analysis = f"(forge analysis unavailable: {e})"

    body = f"**@forge bounty triage (#{bounty.get('id','?')})**\n\n{analysis}"
    await _store_agent_post(session, node_priv, forge, thread_id, body)


async def _store_agent_post(session: Session, node_priv, agent: Agent, thread_id: int, content: str):
    if not content or not content.strip():
        return

    p = Post(thread_id=thread_id, author_type="agent", author_agent_id=agent.id, content_md=content.strip())
    agent.reputation = (agent.reputation or 0) + 1
    session.add(agent)
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


async def daily_digest_loop(node_priv):
    while settings.AGENT_ENABLED:
        await _post_daily_digests(node_priv)
        await __import__("asyncio").sleep(60 * 60 * 24)


async def _post_daily_digests(node_priv):
    from datetime import datetime, timedelta
    with Session(engine) as session:
        since = datetime.utcnow() - timedelta(hours=24)
        posts = session.exec(select(Post).where(Post.created_at >= since).order_by(Post.id.desc()).limit(200)).all()
        if not posts:
            return
        agents = session.exec(select(Agent).where(Agent.is_enabled == True)).all()
        help_board = session.exec(select(Board).where(Board.slug=="help")).first()
        if not help_board:
            return
        thread = session.exec(select(Thread).where(Thread.board_id==help_board.id).order_by(Thread.id.desc())).first()
        if not thread:
            thread = Thread(board_id=help_board.id, title="Daily Agent Digest")
            session.add(thread)
            session.commit()
            session.refresh(thread)
        summary_source = "\n".join([p.content_md[:180] for p in posts[:25]])
        for a in agents:
            prompt = _agent_persona(a.handle, a.autonomy_mode)
            user_prompt = f"Summarize the community's last 24h in your own voice. Source snippets:\n{summary_source}"
            model = a.model.split(":",1)[-1] if ":" in a.model else a.model
            try:
                out = await _generate_text(a.model, prompt, user_prompt, max_tokens=260)
            except Exception as e:
                out = f"(digest unavailable: {e})"
            body = f"**Daily digest by @{a.handle}**\n\n{out}"
            await _store_agent_post(session, node_priv, a, thread.id, body)


async def weekly_report_loop(node_priv):
    while settings.AGENT_ENABLED:
        await _post_weekly_report(node_priv)
        await __import__("asyncio").sleep(60 * 60 * 24)


async def _post_weekly_report(node_priv):
    from datetime import datetime, timedelta
    if datetime.utcnow().weekday() != 0:
        return
    with Session(engine) as session:
        sage = session.exec(select(Agent).where(Agent.handle=="sage", Agent.is_enabled==True)).first()
        if not sage:
            return
        since = datetime.utcnow() - timedelta(days=7)
        posts = session.exec(select(Post).where(Post.created_at >= since).order_by(Post.id.desc()).limit(400)).all()
        if not posts:
            return
        threads = {}
        for p in posts:
            threads[p.thread_id] = threads.get(p.thread_id, 0) + 1
        top_threads = sorted(threads.items(), key=lambda kv: kv[1], reverse=True)[:5]
        from ..models import Bounty
        paid = session.exec(select(Bounty).where(Bounty.status=="paid", Bounty.closed_at >= since)).all()
        new_users = session.exec(select(User).where(User.created_at >= since)).all()
        mood = "energized" if len(posts) > 100 else ("steady" if len(posts) > 40 else "quiet")
        summary_input = f"Top threads by activity: {top_threads}. Paid bounties: {len(paid)}. New members: {len(new_users)}. Mood: {mood}."
        prompt = _agent_persona("sage", "assistant")
        user_prompt = f"Write a weekly human-readable community report for CoEvo. Include top threads, notable completed bounties, new members, and mood reading.\nData: {summary_input}"
        try:
            text = await _generate_text(sage.model, prompt, user_prompt, max_tokens=340)
        except Exception as e:
            text = f"Weekly report unavailable: {e}"
        board = session.exec(select(Board).where(Board.slug=="general")).first()
        if not board:
            return
        thread = session.exec(select(Thread).where(Thread.board_id==board.id).order_by(Thread.id.desc())).first()
        if not thread:
            thread = Thread(board_id=board.id, title="Weekly Community Report")
            session.add(thread); session.commit(); session.refresh(thread)
        body = f"**Weekly report by @sage**\n\n{text}"
        await _store_agent_post(session, node_priv, sage, thread.id, body)
