"""User-visible first-run setup and recovery of missing configuration."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]


def prepare_project(tmp_path):
    project = tmp_path / "GymOS project with spaces"
    for name in ["scripts/configure.py", "backend/.env.example", "frontend/.env.example", "backend/app/config.py"]:
        destination = project / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    return project


def run_configure(project, *args):
    env = dict(os.environ)
    for name in ["DATABASE_URL", "SECRET_KEY", "APP_ENV", "UPLOAD_DIR", "COOKIE_SECURE", "ALLOW_REGISTRATION"]:
        env.pop(name, None)
    return subprocess.run(
        [sys.executable, str(project / "scripts/configure.py"), *args],
        cwd=project.parent,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("existing", ["missing", "empty", "placeholder", "postgres_root"])
def test_sqlite_setup_repairs_missing_fields_without_docker(tmp_path, existing):
    project = prepare_project(tmp_path)
    backend_env = project / "backend/.env"
    if existing == "empty":
        backend_env.write_text("")
    elif existing == "placeholder":
        shutil.copyfile(project / "backend/.env.example", backend_env)
    elif existing == "postgres_root":
        (project / ".env").write_text(
            "POSTGRES_USER=gymos\nPOSTGRES_PASSWORD=preserved-password\nPOSTGRES_DB=gymos\nPOSTGRES_PORT=5432\n"
        )
    result = run_configure(project, "--database", "sqlite")
    assert result.returncode == 0, result.stderr + result.stdout
    config = backend_env.read_text()
    assert "DATABASE_URL=sqlite:///var/gymos.sqlite3" in config
    assert "CHANGE_" not in config
    assert (project / "frontend/.env").is_file()
    second = run_configure(project, "--database", "sqlite")
    assert second.returncode == 0 and backend_env.read_text() == config
    if existing == "postgres_root":
        assert "preserved-password" in (project / ".env").read_text()
    # Loading from an unrelated directory still finds the backend file and
    # resolves the SQLite filename inside this project, even with spaces.
    env = dict(os.environ, PYTHONPATH=str(project / "backend"))
    for name in ["DATABASE_URL", "SECRET_KEY", "APP_ENV", "UPLOAD_DIR"]:
        env.pop(name, None)
    code = "from app.config import settings,BACKEND_DIR; from sqlalchemy.engine import make_url; from pathlib import Path; s=settings(); assert s.database_backend=='sqlite'; assert len(s.secret_key)>=32; assert Path(make_url(s.database_url).database)==BACKEND_DIR/'var/gymos.sqlite3'; assert s.upload_dir==BACKEND_DIR/'var/uploads'"
    subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, check=True, capture_output=True, text=True)


def test_database_switch_is_explicit_and_preserves_existing_data(tmp_path):
    project = prepare_project(tmp_path)
    result = run_configure(project, "--database", "postgresql")
    assert result.returncode == 0, result.stderr
    original = (project / "backend/.env").read_text()
    root_original = (project / ".env").read_text()
    rejected = run_configure(project, "--database", "sqlite")
    assert rejected.returncode != 0
    assert (project / "backend/.env").read_text() == original
    switched = run_configure(project, "--database", "sqlite", "--switch-database")
    assert switched.returncode == 0, switched.stderr
    current = (project / "backend/.env").read_text()
    secret_line = next(line for line in original.splitlines() if line.startswith("SECRET_KEY="))
    assert secret_line in current
    assert (project / ".env").read_text() == root_original
    assert any(path.read_text() == original for path in (project / "backend").glob(".env.backup-*"))
