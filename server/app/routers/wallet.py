from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..models import Wallet, LedgerTx, User
from ..schemas import TipIn
from ..deps import get_current_user
from ..services.ledger import transfer
from ..services.events_log import log_event

router = APIRouter(prefix="/api/wallet", tags=["wallet"])

@router.get("")
def get_wallet(session: Session = Depends(get_session), user=Depends(get_current_user)):
    w = session.exec(select(Wallet).where(Wallet.owner_type=="user", Wallet.owner_user_id==user.id)).first()
    if not w:
        raise HTTPException(404, "Wallet missing")
    txs = session.exec(select(LedgerTx).where(
        (LedgerTx.from_wallet_id==w.id) | (LedgerTx.to_wallet_id==w.id)
    ).order_by(LedgerTx.id.desc()).limit(50)).all()

    return {
        "wallet": {"id": w.id, "balance": w.balance},
        "ledger": [{
            "id": t.id,
            "from_wallet_id": t.from_wallet_id,
            "to_wallet_id": t.to_wallet_id,
            "amount": t.amount,
            "reason": t.reason,
            "ref_type": t.ref_type,
            "ref_id": t.ref_id,
            "created_at": t.created_at.isoformat()+"Z",
            "signature": t.signature
        } for t in txs]
    }

@router.post("/tip")
def tip(payload: TipIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    if payload.amount <= 0:
        raise HTTPException(400, "Amount must be > 0")
    from_w = session.exec(select(Wallet).where(Wallet.owner_type=="user", Wallet.owner_user_id==user.id)).first()
    if not from_w:
        raise HTTPException(404, "Wallet missing")

    to_user = session.exec(select(User).where(User.handle==payload.to_handle)).first()
    if not to_user:
        raise HTTPException(404, "Recipient not found")
    to_w = session.exec(select(Wallet).where(Wallet.owner_type=="user", Wallet.owner_user_id==to_user.id)).first()
    if not to_w:
        raise HTTPException(404, "Recipient wallet missing")

    try:
        tx = transfer(session, from_w.id, to_w.id, payload.amount, "tip", ref_type="user", ref_id=to_user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    log_event(session, "tip_sent", {"from": user.handle, "to": to_user.handle, "amount": payload.amount, "tx_id": tx.id})
    return {"ok": True, "tx_id": tx.id}
