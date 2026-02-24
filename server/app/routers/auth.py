from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..db import get_session
from ..models import User, Wallet
from ..schemas import RegisterIn, LoginIn, TokenOut, UserOut
from ..core.security import hash_password, verify_password, create_access_token
from ..services.ledger import transfer
from ..services.events_log import log_event

router = APIRouter(prefix="/api/auth", tags=["auth"])

NEW_ACCOUNT_GRANT = 50  # default rewards

@router.post("/register", response_model=UserOut)
def register(payload: RegisterIn, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.handle == payload.handle)).first()
    if existing:
        raise HTTPException(400, "Handle already taken")

    user = User(handle=payload.handle, email=payload.email, password_hash=hash_password(payload.password), role="user")
    session.add(user)
    session.commit()
    session.refresh(user)

    wallet = Wallet(owner_type="user", owner_user_id=user.id, balance=0)
    session.add(wallet)
    session.commit()
    session.refresh(wallet)

    transfer(session, None, wallet.id, NEW_ACCOUNT_GRANT, "mint", ref_type="user", ref_id=user.id)
    log_event(session, "user_registered", {"user_id": user.id, "handle": user.handle, "grant": NEW_ACCOUNT_GRANT})

    return UserOut(id=user.id, handle=user.handle, role=user.role)

@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.handle == payload.handle)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token(user.handle)
    log_event(session, "user_login", {"user_id": user.id, "handle": user.handle})
    return TokenOut(access_token=token)
