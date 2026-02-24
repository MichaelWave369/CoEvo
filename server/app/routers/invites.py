import secrets
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ..db import get_session
from ..deps import get_current_user
from ..models import InviteCode

router = APIRouter(prefix="/api/invites", tags=["invites"])

@router.get('/me')
def my_invite(session: Session = Depends(get_session), user=Depends(get_current_user)):
    row = session.exec(select(InviteCode).where(InviteCode.inviter_user_id==user.id)).first()
    if not row:
        code = f"{user.handle}-{secrets.token_hex(4)}"
        row = InviteCode(inviter_user_id=user.id, code=code)
        session.add(row)
        session.commit()
        session.refresh(row)
    return {"code": row.code, "invite_link": f"/?invite={row.code}"}
