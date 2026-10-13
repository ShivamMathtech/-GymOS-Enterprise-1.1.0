"""Engine configuration shared by the application and Alembic."""

from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


def build_engine(url, *, pool_size=10, migration=False):
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            parsed,
            pool_size=pool_size,
            max_overflow=0,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False, "timeout": 30},
        )

        @event.listens_for(engine, "connect")
        def sqlite_connect(connection, record):
            # Own BEGIN explicitly, including SELECT and DDL transactions.
            connection.isolation_level = None
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=FULL")
            cursor.close()

        @event.listens_for(engine, "begin")
        def sqlite_begin(connection):
            # SELECT FOR UPDATE is unavailable in SQLite. Reserve the writer
            # before any reads so a check-then-write workflow is serialized
            # across API workers and the separate notification process.
            connection.exec_driver_sql("BEGIN IMMEDIATE")

        return engine
    return create_engine(
        parsed,
        pool_pre_ping=True,
        pool_size=1 if migration else pool_size,
        max_overflow=0 if migration else 20,
        connect_args={"prepare_threshold": None},
    )


def insert_for(db, table):
    """Return the native insert so ON CONFLICT works on either backend."""
    factory = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    return factory(table)
