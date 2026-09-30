from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apc.models import Base
from apc.settings import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def session_scope():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
