"""SQLAlchemy Engine und Session-Handling.

Der LangGraph-Graph bleibt frei von Session-Handling; die Persistenz macht
der CLI-Runner drumherum. Diese Modulfunktionen bedienen API und Skripte.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

# Eine Engine pro Prozess. pool_pre_ping faengt abgelaufene Verbindungen ab.
engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transaktionaler Session-Kontext fuer Skripte: commit am Ende, rollback bei Fehler."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI-Dependency: liefert eine Session je Request und schliesst sie danach."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
