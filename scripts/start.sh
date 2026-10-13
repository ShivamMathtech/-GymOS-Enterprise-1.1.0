#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/configure.py --database "${1:-auto}"
GYMOS_DATABASE=$(python3 scripts/configure.py --show-database)
if [[ "$GYMOS_DATABASE" == "postgresql" ]]; then
    docker compose up -d --wait db
fi
if [[ ! -x backend/.venv/bin/python ]]; then
    python3 -m venv backend/.venv
fi
backend/.venv/bin/python -m pip install -r backend/requirements.txt
(cd backend && .venv/bin/python -m alembic upgrade head && .venv/bin/python -m app.seed)
npm ci --prefix frontend
(cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log) &
GYMOS_API_PID=$!
(cd backend && .venv/bin/python -m app.jobs) &
GYMOS_JOBS_PID=$!
trap 'kill "$GYMOS_API_PID" "$GYMOS_JOBS_PID" 2>/dev/null || true' EXIT
npm run dev --prefix frontend
