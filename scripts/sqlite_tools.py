"""SQLite maintenance uses Python's built-in backup API, including live WAL data."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path

from configure import ROOT, backend_name, read_env


def configured_database():
    url = os.environ.get("DATABASE_URL") or read_env(ROOT / "backend/.env").get(
        "DATABASE_URL", "sqlite:///var/gymos.sqlite3"
    )
    mode = backend_name(url)
    if mode != "sqlite":
        return mode, None
    path = Path(url.split(":///", 1)[1])
    if not path.is_absolute():
        path = ROOT / "backend" / path
    return mode, path.resolve()


def copy_database(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file():
        raise SystemExit(f"SQLite source not found: {source}")
    if source == destination:
        raise SystemExit("Source and destination must be different files")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # O_EXCL never clobbers a user's database or earlier backup.
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        with closing(
            sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=30)
        ) as origin, closing(sqlite3.connect(destination, timeout=30)) as target:
            origin.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("SQLite integrity check failed")
            if target.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise RuntimeError("SQLite foreign-key check failed")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination
