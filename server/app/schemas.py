from typing import Optional, List
from pydantic import BaseModel, Field

class RegisterIn(BaseModel):
    handle: str = Field(min_length=3, max_length=32)
    email: Optional[str] = None
    password: str = Field(min_length=6, max_length=128)
    invite_code: Optional[str] = None

class LoginIn(BaseModel):
    handle: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    handle: str
    role: str

class BoardOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    subscribed: bool = False

class ThreadOut(BaseModel):
    id: int
    board_id: int
    title: str

class PostOut(BaseModel):
    id: int
    thread_id: int
    author_type: str
    author_handle: str
    content_md: str
    created_at: str
    is_hidden: bool = False
    signature: Optional[str] = None

class CreateBoardIn(BaseModel):
    slug: str
    title: str
    description: str = ""

class CreateThreadIn(BaseModel):
    title: str

class CreatePostIn(BaseModel):
    content_md: str

class CreateRepoIn(BaseModel):
    url: str
    title: str = ""
    description: str = ""
    tags: List[str] = []

class TipIn(BaseModel):
    to_handle: str
    amount: int

class CreateBountyIn(BaseModel):
    amount: int
    title: str
    requirements_md: str = ""

class SubmitBountyIn(BaseModel):
    note_md: str = ""

class PayBountyIn(BaseModel):
    accept: bool = True

class ReportPostIn(BaseModel):
    reason: str = ""

class HidePostIn(BaseModel):
    hide: bool = True

class ToggleSubIn(BaseModel):
    subscribe: bool = True

class ToggleWatchIn(BaseModel):
    watch: bool = True

class MarkReadIn(BaseModel):
    read: bool = True


class ReactIn(BaseModel):
    reaction: str = Field(min_length=1, max_length=24)

class UpdateBioIn(BaseModel):
    bio: str = ""
