"""Create local configuration with the Python standard library; no pip or Docker needed."""

import argparse
import os
import secrets
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def read_env(path):
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def private_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(text)


def backend_name(url):
    if url.startswith(("sqlite:///", "sqlite+pysqlite:///")):
        return "sqlite"
    if url.startswith("postgresql+psycopg://"):
        return "postgresql"
    raise SystemExit(
        "Unsupported DATABASE_URL. Use sqlite:///var/gymos.sqlite3 or postgresql+psycopg://..."
    )


def is_placeholder(value):
    return not value or "CHANGE_" in value


def write_values(path, values):
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    lines = existing.splitlines()
    remaining = dict(values)
    for index, line in enumerate(lines):
        stripped = line.strip().removeprefix("export ")
        if not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                lines[index] = key + "=" + remaining.pop(key)
    lines.extend(key + "=" + value for key, value in remaining.items())
    text = "\n".join(lines) + "\n"
    if text == existing:
        return
    if path.exists():
        backup = path.with_name(path.name + ".backup-" + secrets.token_hex(4))
        private_write(backup, existing)
        temporary = path.with_name(path.name + ".tmp-" + secrets.token_hex(4))
        private_write(temporary, text)
        os.replace(temporary, path)
    else:
        private_write(path, text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database", choices=["auto", "sqlite", "postgresql"], default="auto"
    )
    parser.add_argument(
        "--switch-database",
        action="store_true",
        help="Explicitly select a different database; preserves the old .env and data",
    )
    parser.add_argument(
        "--show-database",
        action="store_true",
        help="Print only the configured backend name",
    )
    args = parser.parse_args()
    backend_path = ROOT / "backend/.env"
    old = read_env(backend_path)
    existing_url = old.get("DATABASE_URL", "")
    if args.show_database:
        print(
            backend_name(
                os.environ.get("DATABASE_URL")
                or existing_url
                or "sqlite:///var/gymos.sqlite3"
            )
        )
        return
    if os.environ.get("DATABASE_URL"):
        raise SystemExit(
            "DATABASE_URL is set in this terminal. Clear that override before local setup so the launcher uses backend/.env. PowerShell: Remove-Item Env:DATABASE_URL"
        )
    root_values = read_env(ROOT / ".env")
    current_mode = backend_name(existing_url) if existing_url else None
    chosen = (
        args.database
        if args.database != "auto"
        else current_mode
        or ("postgresql" if root_values.get("POSTGRES_DB") else "sqlite")
    )
    if current_mode and current_mode != chosen and not args.switch_database:
        raise SystemExit(
            f"Existing {current_mode} configuration preserved. To explicitly use a separate {chosen} database, run: py -3.12 scripts/configure.py --database {chosen} --switch-database"
        )
    switching = current_mode is not None and current_mode != chosen
    changes = {}
    if chosen == "sqlite":
        if not existing_url or switching:
            changes["DATABASE_URL"] = "sqlite:///var/gymos.sqlite3"
        (ROOT / "backend/var").mkdir(parents=True, exist_ok=True)
    else:
        defaults = {
            "POSTGRES_USER": "gymos",
            "POSTGRES_DB": "gymos",
            "POSTGRES_PORT": "5432",
            "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        }
        root_changes = {
            key: value
            for key, value in defaults.items()
            if is_placeholder(root_values.get(key))
        }
        root_values.update(root_changes)
        # Preserve pre-existing custom PostgreSQL connection settings.
        if not existing_url or switching or is_placeholder(existing_url):
            write_values(ROOT / ".env", root_changes)
            user = quote(root_values["POSTGRES_USER"], safe="")
            password = quote(root_values["POSTGRES_PASSWORD"], safe="")
            database = quote(root_values["POSTGRES_DB"], safe="")
            changes["DATABASE_URL"] = (
                f"postgresql+psycopg://{user}:{password}@127.0.0.1:{root_values['POSTGRES_PORT']}/{database}"
            )
    template = read_env(ROOT / "backend/.env.example")
    changes.update(
        {
            key: value
            for key, value in template.items()
            if key not in old and key not in {"DATABASE_URL", "SECRET_KEY"}
        }
    )
    if is_placeholder(old.get("SECRET_KEY")) or len(old.get("SECRET_KEY", "")) < 32:
        changes["SECRET_KEY"] = secrets.token_hex(48)
    write_values(backend_path, changes)
    frontend = ROOT / "frontend/.env"
    if not frontend.exists():
        private_write(
            frontend, (ROOT / "frontend/.env.example").read_text(encoding="utf-8")
        )
    print(
        f"Local {chosen} configuration ready. Existing valid secrets and data are preserved."
    )
    if switching:
        print(
            "The selected database is independent. Existing records were not transferred; the previous .env was backed up."
        )
    if chosen == "sqlite":
        print(
            "Default database: backend/var/gymos.sqlite3. No Docker or database server required."
        )


if __name__ == "__main__":
    main()
