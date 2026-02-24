import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from .core.config import settings
from .db import init_db, engine
from .models import Board, User, Wallet, Agent
from .deps import get_current_user
from .routers import auth, boards, subscriptions, threads, events, artifacts, repos, wallet, bounties, agents, moderation, system, notifications, watches, audit, invites, profiles, reactions, public, votes, devapi
from .core.node_signing import load_or_create_node_key, public_key_pem
from .services import ledger as ledger_service
from .services import events_log as events_log_service
from .routers import threads as threads_router
from .agents.runner import agent_loop, daily_digest_loop
from .core.security import hash_password

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NODE_PRIV, NODE_PUB = load_or_create_node_key(settings.NODE_KEY_PATH)
NODE_PUBLIC_KEY_PEM = public_key_pem(NODE_PUB)

ledger_service.set_node_priv(NODE_PRIV)
events_log_service.set_node_priv(NODE_PRIV)
threads_router.set_node_priv(NODE_PRIV)

def seed_boards(session: Session):
    existing = session.exec(select(Board)).first()
    if not existing:
        session.add(Board(slug="general", title="General", description="General discussion"))
        session.add(Board(slug="help", title="Help", description="Ask for help / mention agents (@sage)"))
        session.add(Board(slug="dev", title="Dev", description="Development, repos, and artifacts"))
        session.commit()

def seed_default_agents(session: Session):
    defaults = [
        ("sage", "assistant"),
        ("nova", "explorer"),
        ("forge", "peer"),
        ("echo", "explorer"),
    ]
    for handle, autonomy_mode in defaults:
        a = session.exec(select(Agent).where(Agent.handle==handle)).first()
        if not a:
            a = Agent(handle=handle, model=f"anthropic:{settings.DEFAULT_AGENT_MODEL}", autonomy_mode=autonomy_mode, is_enabled=True)
            session.add(a)
            session.commit()
            session.refresh(a)
            w = Wallet(owner_type="agent", owner_agent_id=a.id, balance=0)
            session.add(w)
            session.commit()

def seed_admin(session: Session):
    if not settings.SEED_ADMIN:
        return
    admin = session.exec(select(User).where(User.handle=="admin")).first()
    if not admin:
        admin = User(handle="admin", email=None, password_hash=hash_password(settings.ADMIN_PASSWORD), role="admin")
        session.add(admin)
        session.commit()
        session.refresh(admin)
        w = Wallet(owner_type="user", owner_user_id=admin.id, balance=0)
        session.add(w)
        session.commit()
    else:
        admin.role = "admin"
        admin.password_hash = hash_password(settings.ADMIN_PASSWORD)
        session.add(admin)
        session.commit()

@app.on_event("startup")
async def on_startup():
    init_db()
    with Session(engine) as session:
        seed_boards(session)
        seed_default_agents(session)
        seed_admin(session)

    if settings.AGENT_ENABLED:
        asyncio.create_task(agent_loop(NODE_PRIV))
        asyncio.create_task(daily_digest_loop(NODE_PRIV))

@app.get("/api/health")
def health():
    return {"ok": True, "app": settings.APP_NAME, "agents_enabled": settings.AGENT_ENABLED}

@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "handle": user.handle, "role": user.role}

app.include_router(auth.router)
app.include_router(boards.router)
app.include_router(subscriptions.router)
app.include_router(threads.router)
app.include_router(events.router)
app.include_router(artifacts.router)
app.include_router(repos.router)
app.include_router(wallet.router)
app.include_router(bounties.router)
app.include_router(agents.router)
app.include_router(moderation.router)
app.include_router(system.router)
app.include_router(notifications.router)
app.include_router(watches.router)
app.include_router(audit.router)

app.include_router(invites.router)
app.include_router(profiles.router)
app.include_router(reactions.router)
app.include_router(public.router)

app.include_router(votes.router)
app.include_router(devapi.router)
