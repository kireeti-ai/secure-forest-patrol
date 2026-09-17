from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_database_url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = get_database_url()
    connect_args: dict[str, object] = {}
    if make_url(url).get_backend_name() == "postgresql":
        # Every forest timestamp is stored timezone-aware in UTC. Pinning the
        # session timezone makes PostgreSQL return TIMESTAMPTZ values as UTC,
        # so API responses are unambiguous for the dashboard instead of being
        # rendered in the server's local offset.
        connect_args["options"] = "-c timezone=UTC"
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


SessionLocal = sessionmaker(autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal(bind=get_engine())
    try:
        yield db
    finally:
        db.close()
