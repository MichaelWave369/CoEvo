from __future__ import annotations
from datetime import datetime
from sqlmodel import Session, select
from ..models import Wallet, LedgerTx
from ..core.node_signing import sign

_NODE_PRIV = None

def set_node_priv(priv):
    global _NODE_PRIV
    _NODE_PRIV = priv

def get_or_create_system_wallet(session: Session) -> Wallet:
    w = session.exec(select(Wallet).where(Wallet.owner_type == "system")).first()
    if w:
        return w
    w = Wallet(owner_type="system", balance=0, updated_at=datetime.utcnow())
    session.add(w)
    session.commit()
    session.refresh(w)
    return w

def transfer(session: Session, from_wallet_id: int | None, to_wallet_id: int, amount: int, reason: str, ref_type: str="system", ref_id: int|None=None):
    if amount <= 0:
        raise ValueError("Amount must be > 0")
    if from_wallet_id is not None:
        from_w = session.get(Wallet, from_wallet_id)
        if not from_w:
            raise ValueError("From wallet not found")
        if from_w.balance < amount:
            raise ValueError("Insufficient balance")
        from_w.balance -= amount
        from_w.updated_at = datetime.utcnow()
        session.add(from_w)

    to_w = session.get(Wallet, to_wallet_id)
    if not to_w:
        raise ValueError("To wallet not found")
    to_w.balance += amount
    to_w.updated_at = datetime.utcnow()
    session.add(to_w)

    tx = LedgerTx(
        from_wallet_id=from_wallet_id,
        to_wallet_id=to_wallet_id,
        amount=amount,
        reason=reason,
        ref_type=ref_type,
        ref_id=ref_id
    )

    if _NODE_PRIV is not None:
        payload = {
            "from_wallet_id": tx.from_wallet_id,
            "to_wallet_id": tx.to_wallet_id,
            "amount": tx.amount,
            "reason": tx.reason,
            "ref_type": tx.ref_type,
            "ref_id": tx.ref_id,
            "created_at": tx.created_at.isoformat()+"Z",
        }
        tx.signature = sign(_NODE_PRIV, payload)

    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx
