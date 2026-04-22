from backend.app.db.models import Base
from backend.app.db.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
