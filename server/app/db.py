from sqlmodel import SQLModel, create_engine, Session
from .core.config import settings

engine = create_engine(settings.DB_URL, echo=False, connect_args={"check_same_thread": False})

def init_db() -> None:
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
