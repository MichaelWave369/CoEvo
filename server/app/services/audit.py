from __future__ import annotations
import io
import json
import zipfile
from datetime import datetime
from sqlmodel import Session, select
from ..models import Post, LedgerTx, EventLog, Notification
from ..core.config import settings
from ..core.node_signing import load_or_create_node_key, public_key_pem


def _node_public_key_pem() -> str:
    _, pub = load_or_create_node_key(settings.NODE_KEY_PATH)
    return public_key_pem(pub)


def export_audit_zip(session: Session) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        meta = {
            "exported_at": datetime.utcnow().isoformat()+"Z",
            "public_key_pem": _node_public_key_pem(),
        }
        z.writestr("meta.json", json.dumps(meta, indent=2))

        def add_jsonl(name: str, rows: list[dict]):
            content = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else "")
            z.writestr(name, content)

        posts = session.exec(select(Post).order_by(Post.id)).all()
        add_jsonl("posts.jsonl", [{
            "id": p.id,
            "thread_id": p.thread_id,
            "author_type": p.author_type,
            "author_user_id": p.author_user_id,
            "author_agent_id": p.author_agent_id,
            "content_md": p.content_md,
            "created_at": p.created_at.isoformat()+"Z",
            "is_hidden": p.is_hidden,
            "signature": p.signature
        } for p in posts])

        txs = session.exec(select(LedgerTx).order_by(LedgerTx.id)).all()
        add_jsonl("ledger.jsonl", [{
            "id": t.id,
            "from_wallet_id": t.from_wallet_id,
            "to_wallet_id": t.to_wallet_id,
            "amount": t.amount,
            "reason": t.reason,
            "ref_type": t.ref_type,
            "ref_id": t.ref_id,
            "created_at": t.created_at.isoformat()+"Z",
            "signature": t.signature
        } for t in txs])

        evs = session.exec(select(EventLog).order_by(EventLog.id)).all()
        add_jsonl("events.jsonl", [{
            "id": e.id,
            "event_type": e.event_type,
            "payload": e.payload,
            "created_at": e.created_at.isoformat()+"Z",
            "signature": e.signature
        } for e in evs])

        notifs = session.exec(select(Notification).order_by(Notification.id)).all()
        add_jsonl("notifications.jsonl", [{
            "id": n.id,
            "user_id": n.user_id,
            "thread_id": n.thread_id,
            "event_type": n.event_type,
            "payload": n.payload,
            "created_at": n.created_at.isoformat()+"Z",
            "read_at": n.read_at.isoformat()+"Z" if n.read_at else None
        } for n in notifs])

    return buf.getvalue()
