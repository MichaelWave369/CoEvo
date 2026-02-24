from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..deps import get_current_user
from ..models import VoteProposal, VoteBallot
from ..schemas import CreateVoteIn, CastVoteIn
from ..core.events import broker

router = APIRouter(prefix='/api/votes', tags=['votes'])

@router.get('')
def list_votes(session: Session = Depends(get_session), user=Depends(get_current_user)):
    rows = session.exec(select(VoteProposal).order_by(VoteProposal.id.desc())).all()
    out = []
    for r in rows:
        ballots = session.exec(select(VoteBallot).where(VoteBallot.proposal_id==r.id)).all()
        yes = sum(1 for b in ballots if b.vote == 'yes')
        no = sum(1 for b in ballots if b.vote == 'no')
        out.append({
            'id': r.id, 'title': r.title, 'proposal_type': r.proposal_type, 'details_md': r.details_md,
            'status': r.status, 'created_at': r.created_at.isoformat()+"Z", 'yes': yes, 'no': no,
        })
    return out

@router.post('')
async def propose(payload: CreateVoteIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    p = VoteProposal(title=payload.title, proposal_type=payload.proposal_type, details_md=payload.details_md, proposed_by_user_id=user.id)
    session.add(p)
    session.commit()
    session.refresh(p)
    await broker.publish({"type":"vote_proposed", "proposal_id": p.id, "title": p.title, "details_md": p.details_md, "proposal_type": p.proposal_type})
    return {'id': p.id}

@router.post('/{proposal_id}/cast')
def cast_vote(proposal_id: int, payload: CastVoteIn, session: Session = Depends(get_session), user=Depends(get_current_user)):
    prop = session.get(VoteProposal, proposal_id)
    if not prop:
        raise HTTPException(404, 'Proposal not found')
    if payload.vote not in ('yes','no'):
        raise HTTPException(400, 'vote must be yes or no')
    existing = session.exec(select(VoteBallot).where(VoteBallot.proposal_id==proposal_id, VoteBallot.voter_user_id==user.id)).first()
    if existing:
        existing.vote = payload.vote
        existing.rationale = payload.rationale
        session.add(existing)
        session.commit()
        return {'ok': True, 'updated': True}
    b = VoteBallot(proposal_id=proposal_id, voter_user_id=user.id, vote=payload.vote, rationale=payload.rationale)
    session.add(b)
    session.commit()
    return {'ok': True, 'updated': False}
