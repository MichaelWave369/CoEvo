import os
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..models import Thread, Post, Agent
from ..core.events import broker

router = APIRouter(prefix='/api/webhooks', tags=['webhooks'])


@router.post('/nevora/thread/{thread_id}')
async def nevora_to_thread(thread_id: int, payload: dict, x_coevo_webhook_secret: str | None = Header(default=None), session: Session = Depends(get_session)):
    secret = os.getenv('COEVO_WEBHOOK_SECRET', '').strip()
    if secret and x_coevo_webhook_secret != secret:
        raise HTTPException(401, 'Invalid webhook secret')

    t = session.get(Thread, thread_id)
    if not t:
        raise HTTPException(404, 'Thread not found')

    forge = session.exec(select(Agent).where(Agent.handle=='forge')).first()
    content = payload.get('content_md') or payload.get('text') or payload.get('message') or ''
    source = payload.get('source', 'nevora')
    if not content.strip():
        raise HTTPException(400, 'content missing')

    p = Post(
        thread_id=thread_id,
        author_type='agent' if forge else 'user',
        author_agent_id=forge.id if forge else None,
        content_md=f"**Webhook event ({source})**\n\n{content.strip()}",
    )
    session.add(p)
    session.commit()
    session.refresh(p)

    await broker.publish({
        'type': 'post_created',
        'thread_id': thread_id,
        'post': {
            'id': p.id,
            'thread_id': p.thread_id,
            'author_type': p.author_type,
            'author_handle': forge.handle if forge else 'webhook',
            'content_md': p.content_md,
            'created_at': p.created_at.isoformat() + 'Z',
            'is_hidden': p.is_hidden,
            'signature': p.signature,
        }
    })
    return {'ok': True, 'post_id': p.id}
