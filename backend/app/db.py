import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import inspect, text


DB_PATH = Path(os.getenv("ENT_DB_PATH", "data/ent_research.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_latest_schema() -> None:
    inspector = inspect(engine)
    if "publications" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("publications")}
    if "abstract" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE publications ADD COLUMN abstract TEXT"))
