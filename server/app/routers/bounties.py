from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..models import Bounty, Wallet, Thread, Post
from ..schemas import CreateBountyIn, SubmitBountyIn, PayBountyIn
from ..deps import get_current_user
from ..services.ledger import get_or_create_system_wallet, transfer
from ..services.events_log import log_event
from ..core.events import broker

router = APIRouter(prefix="/api/bounties", tags=["bounties"])

@router.get("")
def list_bounties(session: Session = Depends(get_session), user=Depends(get_current_user)):
    bounties = session.exec(select(Bounty).order_by(Bounty.id.desc())).all()
    return [{
        "id": b.id, "thread_id": b.thread_id, "creator_user_id": b.creator_user_id,
        "amount": b.amount, "title": b.title, "requirements_md": b.requirements_md,
        "status": b.status, "claimed_by_user_id": b.claimed_by_user_id,
        "created_at": b.created_at.isoformat()+"Z",
        "closed_at": b.closed_at.isoformat()+"Z" if b.closed_at else None
    } for b in bounties]

@router.get("/thread/{thread_id}")
def list_for_thread(thread_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    bounties = session.exec(select(Bounty).where(Bounty.thread_id==thread_id).order_by(Bounty.id.desc())).all()
    return [{
        "id": b.id, "thread_id": b.thread_id, "creator_user_id": b.creator_user_id,
        "amount": b.amount, "title": b.title, "requirements_md": b.requirements_md,
        "status": b.status, "claimed_by_user_id": b.claimed_by_user_id,
        "created_at": b.created_at.isoformat()+"Z",
        "closed_at": b.closed_at.isoformat()+"Z" if b.closed_at else None
    } for b in bounties]

@router.post("/thread/{thread_id}")
async def create_bounty(thread_id: int, payload: CreateBountyIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    if payload.amount <= 0:
        raise HTTPException(400, "Amount must be > 0")
    t = session.get(Thread, thread_id)
    if not t:
        raise HTTPException(404, "Thread not found")

    creator_w = session.exec(select(Wallet).where(Wallet.owner_type=="user", Wallet.owner_user_id==user.id)).first()
    if not creator_w:
        raise HTTPException(404, "Wallet missing")
    system_w = get_or_create_system_wallet(session)

    try:
        transfer(session, creator_w.id, system_w.id, payload.amount, "escrow", ref_type="thread", ref_id=thread_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    b = Bounty(thread_id=thread_id, creator_user_id=user.id, amount=payload.amount, title=payload.title, requirements_md=payload.requirements_md)
    session.add(b)
    session.commit()
    session.refresh(b)
    log_event(session, "bounty_created", {"bounty_id": b.id, "thread_id": thread_id, "amount": b.amount, "by": user.handle})
    await broker.publish({
        "type": "bounty_created",
        "thread_id": thread_id,
        "bounty": {
            "id": b.id,
            "title": b.title,
            "amount": b.amount,
            "requirements_md": b.requirements_md,
            "creator_handle": user.handle,
        },
    })
    return {"id": b.id}

@router.post("/{bounty_id}/claim")
def claim_bounty(bounty_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    b = session.get(Bounty, bounty_id)
    if not b:
        raise HTTPException(404, "Not found")
    if b.status != "open":
        raise HTTPException(400, "Not open")
    b.status = "claimed"
    b.claimed_by_user_id = user.id
    session.add(b)
    session.commit()
    log_event(session, "bounty_claimed", {"bounty_id": b.id, "by": user.handle})
    return {"ok": True}

@router.post("/{bounty_id}/submit")
def submit_bounty(bounty_id: int, payload: SubmitBountyIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    b = session.get(Bounty, bounty_id)
    if not b:
        raise HTTPException(404, "Not found")
    if b.status != "claimed":
        raise HTTPException(400, "Not claimed")
    if b.claimed_by_user_id != user.id:
        raise HTTPException(403, "Not your bounty")
    p = Post(thread_id=b.thread_id, author_type="user", author_user_id=user.id, content_md=f"**Bounty submission** (bounty #{b.id}):\n\n{payload.note_md}")
    session.add(p)
    b.status = "submitted"
    session.add(b)
    session.commit()
    log_event(session, "bounty_submitted", {"bounty_id": b.id, "by": user.handle})
    return {"ok": True}

@router.post("/{bounty_id}/pay")
def pay_bounty(bounty_id: int, payload: PayBountyIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    b = session.get(Bounty, bounty_id)
    if not b:
        raise HTTPException(404, "Not found")
    if b.creator_user_id != user.id:
        raise HTTPException(403, "Only creator can pay/cancel")
    if b.status != "submitted":
        raise HTTPException(400, "Bounty not submitted")

    system_w = get_or_create_system_wallet(session)

    if not payload.accept:
        creator_w = session.exec(select(Wallet).where(Wallet.owner_type=="user", Wallet.owner_user_id==user.id)).first()
        if not creator_w:
            raise HTTPException(404, "Wallet missing")
        transfer(session, system_w.id, creator_w.id, b.amount, "refund", ref_type="bounty", ref_id=b.id)
        b.status = "canceled"
        b.closed_at = datetime.utcnow()
        session.add(b)
        session.commit()
        log_event(session, "bounty_refunded", {"bounty_id": b.id, "by": user.handle})
        return {"ok": True, "status": b.status}

    if not b.claimed_by_user_id:
        raise HTTPException(400, "No claimant")
    solver_w = session.exec(select(Wallet).where(Wallet.owner_type=="user", Wallet.owner_user_id==b.claimed_by_user_id)).first()
    if not solver_w:
        raise HTTPException(404, "Solver wallet missing")

    transfer(session, system_w.id, solver_w.id, b.amount, "payout", ref_type="bounty", ref_id=b.id)
    b.status = "paid"
    b.closed_at = datetime.utcnow()
    session.add(b)
    session.commit()
    log_event(session, "bounty_paid", {"bounty_id": b.id, "by": user.handle})
    return {"ok": True, "status": b.status}
