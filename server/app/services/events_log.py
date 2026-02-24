from __future__ import annotations
from sqlmodel import Session
from ..models import EventLog
from ..core.node_signing import sign

_NODE_PRIV = None

def set_node_priv(priv):
    global _NODE_PRIV
    _NODE_PRIV = priv

def log_event(session: Session, event_type: str, payload: dict):
    e = EventLog(event_type=event_type, payload=payload)
    if _NODE_PRIV is not None:
        sig_payload = {
            "event_type": e.event_type,
            "payload": e.payload,
            "created_at": e.created_at.isoformat()+"Z",
        }
        e.signature = sign(_NODE_PRIV, sig_payload)
    session.add(e)
    session.commit()
    session.refresh(e)
    return e
