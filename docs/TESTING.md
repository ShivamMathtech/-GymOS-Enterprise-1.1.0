# Testing

## Default: SQLite, no external database

Backend tests automatically create and migrate a disposable SQLite file outside the project. They never fall back to the developer's `DATABASE_URL` or `backend/var/gymos.sqlite3`. The file is removed when the test run finishes.

From the project root in PowerShell:

```powershell
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Set-Location backend
.venv\Scripts\python.exe -m pytest -ra
.venv\Scripts\python.exe -m ruff check .
```

If `TEST_DATABASE_URL` is already set, clear it to use the temporary SQLite default. An explicitly supplied test database requires `GYMOS_TEST_CONFIRM=isolated`. Never point tests at a database containing records you need.

The same acceptance tests cover authentication, permissions, tenant isolation, memberships, invoices, partial payments/refunds, attendance, QR, booking conflicts, inventory, maintenance, notifications and reports on either backend. SQLite-specific tests verify integer money storage, UTC round trips, foreign-key enforcement, repeat completed visits, live backup/restore, a new-process read, configuration recovery and explicit backend switching. The concurrency tests also run against SQLite.

## Frontend

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run lint
npm.cmd test
npm.cmd run build
npm.cmd audit --omit=dev
```

## Native PostgreSQL integration tests

These commands use a separate disposable database on port 5433; they do not use the development volume.

From the project root in PowerShell:

```powershell
docker compose -f compose.test.yaml up -d --wait
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
$env:TEST_DATABASE_URL = "postgresql+psycopg://gymos_test:isolated-test-only@127.0.0.1:5433/gymos_test"
$env:DATABASE_URL = $env:TEST_DATABASE_URL
$env:GYMOS_TEST_CONFIRM = "isolated"
$env:APP_ENV = "test"
$env:SECRET_KEY = "test-only-randomized-in-ci-not-a-production-secret"
Set-Location backend
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic check
.venv\Scripts\python.exe -m pytest -ra
Set-Location ..
docker compose -f compose.test.yaml down
Remove-Item Env:TEST_DATABASE_URL,Env:DATABASE_URL,Env:GYMOS_TEST_CONFIRM,Env:SECRET_KEY,Env:APP_ENV -ErrorAction SilentlyContinue
```

SQLite-only tests skip on PostgreSQL. Set `TEST_PGLITE=1` only for the PGlite socket adapter: it additionally skips two native concurrency checks and an immutable-trigger rollback check. Never use that flag to validate native PostgreSQL.

## Browser acceptance

Run backend and Vite against a separate disposable SQLite or PostgreSQL test database with `ALLOW_REGISTRATION=true`. In `frontend`:

```text
npx playwright install chromium
npm run test:e2e
```

The supplied Playwright test drives registration, branch/plan/member creation, membership assignment, payment and check-in through the UI. Use a local disposable test server; do not point this at production. Browser E2E was not executed in this build environment.

## Dependency locks and CI

`requirements.txt` and `requirements-dev.txt` pin Python dependencies and hashes. `package-lock.json` locks frontend installation; use `npm ci`. Python's SQLite driver is included in Python; no additional database-server package is required. The existing psycopg dependency remains bundled for optional PostgreSQL support.

CI supplies SQLite jobs on Windows and Linux, plus a native PostgreSQL job with frontend build/tests, browser acceptance and dependency auditing. The CI file is supplied; a remote CI run is not implied. See `VERIFICATION.md` for the actual local results.
