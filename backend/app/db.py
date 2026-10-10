from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    future=True,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_sqlite_schema() -> None:
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    with engine.begin() as conn:
        tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ")).fetchall()
        table_names = {table[0] for table in tables}

        if "accounts" in table_names:
            columns = conn.execute(text("PRAGMA table_info('accounts')")).fetchall()
            existing_columns = {column[1] for column in columns}
            if "broker_config" not in existing_columns:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN broker_config VARCHAR(5000)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
