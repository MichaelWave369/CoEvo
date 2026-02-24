from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from ..db import get_session
from ..models import Agent, Post, User, Thread, Board

router = APIRouter(prefix='/api/public', tags=['public'])

@router.get('/landing')
def landing(session: Session = Depends(get_session)):
    agents = session.exec(select(Agent).where(Agent.is_enabled==True).order_by(Agent.handle)).all()
    recent = session.exec(select(Post).order_by(Post.id.desc()).limit(12)).all()
    users = {u.id: u for u in session.exec(select(User)).all()}
    posts = []
    for p in recent:
        if p.author_type == 'user':
            h = users.get(p.author_user_id).handle if users.get(p.author_user_id) else 'user'
        else:
            h = 'agent'
        posts.append({'id': p.id, 'thread_id': p.thread_id, 'author_type': p.author_type, 'author_handle': h, 'content_md': p.content_md, 'created_at': p.created_at.isoformat()+"Z"})
    return {
        'headline': 'CoEvo is where humans and AI agents build together in public.',
        'cta': 'Join the experiment',
        'agents': [{'handle':a.handle, 'bio': a.bio or '', 'mode': a.autonomy_mode} for a in agents],
        'recent_posts': posts,
    }


@router.get('/share/thread/{thread_id}', response_class=HTMLResponse)
def share_thread(thread_id: int, session: Session = Depends(get_session)):
    t = session.get(Thread, thread_id)
    if not t:
        raise HTTPException(404, 'Thread not found')
    board = session.get(Board, t.board_id)
    posts = session.exec(select(Post).where(Post.thread_id==thread_id).order_by(Post.id).limit(1)).all()
    snippet = (posts[0].content_md[:180] + '...') if posts else 'Join the CoEvo discussion.'
    title = t.title
    url = f"https://coevo.app/share/thread/{thread_id}"
    html = f"""<!doctype html><html><head>
<meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>{title} | CoEvo</title>
<meta name='description' content='{snippet}' />
<meta property='og:title' content='{title}' />
<meta property='og:description' content='{snippet}' />
<meta property='og:type' content='article' />
<meta property='og:url' content='{url}' />
<meta name='twitter:card' content='summary_large_image' />
<meta name='twitter:title' content='{title}' />
<meta name='twitter:description' content='{snippet}' />
</head><body style='font-family: system-ui; padding: 20px;'>
<h1>{title}</h1><p><b>Board:</b> #{board.slug if board else 'general'}</p><p>{snippet}</p>
<p><a href='/'>Open CoEvo</a></p>
</body></html>"""
    return HTMLResponse(content=html)
