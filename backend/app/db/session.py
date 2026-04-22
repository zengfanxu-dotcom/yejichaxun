import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _default_sqlite_url() -> str:
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
    os.makedirs(db_dir, exist_ok=True)
    return f"sqlite:///{os.path.join(db_dir, 'app.db')}"


DATABASE_URL = os.getenv("DATABASE_URL", _default_sqlite_url())

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
