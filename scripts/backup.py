"""Back up the configured SQLite file or PostgreSQL database without overwriting files."""

import argparse
import os
import subprocess
from pathlib import Path

from sqlite_tools import configured_database, copy_database

p = argparse.ArgumentParser()
p.add_argument("output")
p.add_argument("--compose", default="compose.yaml")
p.add_argument("--engine", choices=["auto", "sqlite", "postgresql"], default="auto")
a = p.parse_args()
mode, database_path = (
    ("postgresql", None) if a.engine == "postgresql" else configured_database()
)
if a.engine == "sqlite" and mode != "sqlite":
    raise SystemExit("SQLite backup requires a SQLite DATABASE_URL")
if mode == "sqlite":
    backup_path = copy_database(database_path, a.output)
    print("SQLite backup verified:", backup_path)
    print("Also back up backend/var/uploads to preserve member photos.")
    raise SystemExit(0)
root = Path(__file__).resolve().parents[1]
out = Path(a.output).resolve()
out.parent.mkdir(parents=True, exist_ok=True)
command = [
    "docker",
    "compose",
    "-f",
    a.compose,
    "exec",
    "-T",
    "db",
    "sh",
    "-c",
    'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl',
]
fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
try:
    with os.fdopen(fd, "wb") as f:
        subprocess.run(command, cwd=root, stdout=f, check=True)
except Exception:
    out.unlink(missing_ok=True)
    raise
print("Backup written to", out)
