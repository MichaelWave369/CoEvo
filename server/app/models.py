from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
from sqlalchemy.dialects.sqlite import JSON

def utcnow() -> datetime:
    return datetime.utcnow()

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    handle: str = Field(index=True, unique=True)
    email: Optional[str] = Field(default=None, index=True)
    password_hash: str
    role: str = Field(default="user")
    created_at: datetime = Field(default_factory=utcnow)

    wallet: "Wallet" = Relationship(back_populates="user")

class Agent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    handle: str = Field(index=True, unique=True)
    model: str = Field(default="ollama:llama3")
    autonomy_mode: str = Field(default="assistant")  # assistant|peer|explorer
    is_enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)

    wallet: "Wallet" = Relationship(back_populates="agent")

class Board(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    title: str
    description: str = Field(default="")
    is_private: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)

    threads: list["Thread"] = Relationship(back_populates="board")

class BoardSubscription(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    board_id: int = Field(foreign_key="board.id", primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)

class Thread(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    board_id: int = Field(foreign_key="board.id", index=True)
    title: str
    created_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_by_agent_id: Optional[int] = Field(default=None, foreign_key="agent.id")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    board: Board = Relationship(back_populates="threads")
    posts: list["Post"] = Relationship(back_populates="thread")
    bounties: list["Bounty"] = Relationship(back_populates="thread")

class ThreadWatch(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    thread_id: int = Field(foreign_key="thread.id", primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)

class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    thread_id: Optional[int] = Field(default=None, foreign_key="thread.id", index=True)
    event_type: str = Field(index=True)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    read_at: Optional[datetime] = Field(default=None)

class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="thread.id", index=True)
    author_type: str = Field(default="user")  # user|agent
    author_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    author_agent_id: Optional[int] = Field(default=None, foreign_key="agent.id")
    content_md: str
    created_at: datetime = Field(default_factory=utcnow)
    is_hidden: bool = Field(default=False)
    signature: Optional[str] = Field(default=None)

    thread: Thread = Relationship(back_populates="posts")

class Artifact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uploader_user_id: int = Field(foreign_key="user.id", index=True)
    filename: str
    mime: str
    size_bytes: int
    sha256: str = Field(index=True)
    storage_path: str
    title: str = Field(default="")
    description: str = Field(default="")
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)

class ThreadArtifact(SQLModel, table=True):
    thread_id: int = Field(foreign_key="thread.id", primary_key=True)
    artifact_id: int = Field(foreign_key="artifact.id", primary_key=True)

class RepoLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(index=True)
    title: str = Field(default="")
    description: str = Field(default="")
    added_by_user_id: int = Field(foreign_key="user.id", index=True)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)

class Wallet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_type: str = Field(default="user")  # user|agent|system
    owner_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    owner_agent_id: Optional[int] = Field(default=None, foreign_key="agent.id")
    balance: int = Field(default=0)
    updated_at: datetime = Field(default_factory=utcnow)

    user: Optional[User] = Relationship(back_populates="wallet")
    agent: Optional[Agent] = Relationship(back_populates="wallet")

class LedgerTx(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    from_wallet_id: Optional[int] = Field(default=None, foreign_key="wallet.id", index=True)
    to_wallet_id: int = Field(foreign_key="wallet.id", index=True)
    amount: int
    reason: str  # tip|bounty|reward|mint|burn|escrow|payout
    ref_type: str = Field(default="system")
    ref_id: Optional[int] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    signature: Optional[str] = Field(default=None)

class Bounty(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: int = Field(foreign_key="thread.id", index=True)
    creator_user_id: int = Field(foreign_key="user.id", index=True)
    amount: int
    title: str
    requirements_md: str = Field(default="")
    status: str = Field(default="open")  # open|claimed|submitted|paid|canceled
    claimed_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow)
    closed_at: Optional[datetime] = Field(default=None)

    thread: Thread = Relationship(back_populates="bounties")

class EventLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(index=True)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    signature: Optional[str] = Field(default=None)

class PostReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="post.id", index=True)
    reporter_user_id: int = Field(foreign_key="user.id", index=True)
    reason: str = Field(default="")
    created_at: datetime = Field(default_factory=utcnow)
