# GymOS Enterprise 1.1.0

A gym management application built with React, TypeScript, Vite, Tailwind CSS, FastAPI, SQLAlchemy and Alembic. **SQLite is now the default for a fresh local installation. PostgreSQL remains supported.**

**Windows quick start:** extract the whole ZIP into a new folder and double-click **start-sqlite.bat**. Install Python 3.12 and Node.js 24 first. **No Docker, PostgreSQL installation, database account or database password is needed in SQLite mode.** The launcher generates your configuration, creates the database through migrations and starts the applications.

This is a source distribution, not a standalone executable. The first setup downloads dependencies and requires internet access. Once dependencies are installed, the application can run locally without an external database service.

## What changed in 1.1.0

- SQLite file storage for the existing application modules, with PostgreSQL retained as an option.
- Configuration generation and repair for missing `DATABASE_URL` / `SECRET_KEY` fields.
- `.env`, uploads and relative SQLite paths resolve from the backend directory instead of the terminal's working directory.
- Foreign keys, immutable financial/history triggers and the one-open-visit rule work on both databases.
- SQLite stores money as integer minor units, preserving exact totals and payment/refund sums.
- UTC timestamps survive SQLite round trips; concurrent write workflows reserve the SQLite writer before reading.
- SQLite backup/restore commands and additional persistence, configuration and concurrency tests.

See [Verification](docs/VERIFICATION.md) for executed checks and [Feature status](docs/FEATURE_STATUS.md) for implementation boundaries.

## Windows setup, step by step

1. Install **Python 3.12 (64-bit)** from https://www.python.org/downloads/windows/. Enable the **py launcher** and **Add Python to PATH**. Open a new PowerShell window and check `py -3.12 --version`.
2. Install **Node.js 24 LTS** from https://nodejs.org/. Reopen PowerShell and check `node --version` and `npm.cmd --version`.
3. Extract the ZIP into a new, writable directory such as `E:\OPENCV\GymOS-Enterprise-v1.1.0`. Open the inner `gymos-enterprise` folder containing `start-sqlite.bat`.
4. Double-click **start-sqlite.bat**. In PowerShell, run `.\start-sqlite.bat`. Do not run scripts inside the ZIP viewer.
5. Keep setup open while it generates configuration, installs dependencies, applies migrations and creates the local demo account. It then opens API, notifications and frontend windows.
6. Wait for Vite to report ready, then open **http://localhost:5173**. Keep using `localhost` consistently for sign-in.
7. Open **.local-credentials.txt** in the project root. The organization is **demo-gym**, email **owner@example.com**, and password is randomly generated for your installation.
8. Sign in and start adding records. The demo contains one owner, one branch and one plan; operational lists and metrics start empty.

You do not need to copy `.env.example` or enter a secret manually. `start.bat` also works and preserves an already configured database choice. `start-sqlite.bat` explicitly requests SQLite and refuses to silently replace an existing PostgreSQL configuration.

## Where your data lives

| Item | Location |
|---|---|
| SQLite database | `backend/var/gymos.sqlite3` |
| SQLite live journal files | `backend/var/gymos.sqlite3-wal` and `backend/var/gymos.sqlite3-shm` when present |
| Member photos | `backend/var/uploads/` |
| Backend configuration | `backend/.env` |
| Generated demo credentials | `.local-credentials.txt` |

SQLite is a real database stored locally in a file. Closing or restarting the application preserves records. Do not delete `backend/var` to fix startup problems. Use the backup command below to capture a consistent database snapshot, including committed WAL contents.

## Fix the earlier missing-settings error

The old error meant the backend had no usable `DATABASE_URL` / `SECRET_KEY` configuration. The new launcher generates these settings before starting the app. For a fresh 1.1.0 extraction, use `start-sqlite.bat`.

If configuring manually, run from the project root:

```powershell
py -3.12 scripts\configure.py --database sqlite
```

The helper repairs missing fields, generates a random secret and preserves existing valid values. If the terminal has a `DATABASE_URL` override, remove it first with `Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue`.

## Manual PowerShell setup

Open PowerShell in the inner `gymos-enterprise` folder:

```powershell
py -3.12 scripts\configure.py --database sqlite
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location backend
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m app.seed
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In a second terminal, open the project's `frontend` folder:

```powershell
npm.cmd ci
npm.cmd run dev
```

In a third terminal, open the project's `backend` folder:

```powershell
.venv\Scripts\python.exe -m app.jobs
```

The jobs process provides in-app reminders. No SMTP account or Redis service is needed for local startup. To start with an empty workspace instead of a demo, skip `app.seed` and use **Create a workspace** on the login page.

## Your first workflow

1. **Team & settings → Branches:** set working hours and the gym's time zone. Equal opening/closing times mean 24-hour access.
2. **Memberships → Create plan:** set day duration, price, discount and tax.
3. **Members → Register member:** select the branch and enter a unique phone number.
4. **Memberships → Assign membership:** creates an invoice and pending membership.
5. **Billing → Record payment:** record money actually received. Partial payment leaves a balance; full payment activates access. This does not charge a card or collect UPI funds.
6. **Attendance → Check in member:** validates access, branch, hours and duplicates. Check the member out after the visit.
7. **Overview / Reports:** inspect the resulting metrics and export CSV. Reload or restart: your entries remain saved.

Trainer scheduling, workouts, member portal, inventory, maintenance, refunds and notifications use the same selected database. See [Business rules](docs/BUSINESS_RULES.md) for exact behavior.

## Backup and restore: SQLite

From the project root, while the application is running or stopped:

```powershell
py -3.12 scripts\backup.py backups\gymos-backup.sqlite3
```

Choose a new backup filename each time. Also copy `backend/var/uploads` to preserve photos. Configuration and generated credentials should be kept privately with your recovery records.

Restore to a **new file**:

```powershell
py -3.12 scripts\restore.py backups\gymos-backup.sqlite3 --sqlite-file backend\var\gymos-restored.sqlite3
```

After the command succeeds, stop the API and jobs windows, edit `backend/.env` to set `DATABASE_URL=sqlite:///var/gymos-restored.sqlite3`, restore the matching photos if needed, and restart. The restore helper refuses to overwrite an existing file.

## PostgreSQL option and existing 1.0.0 installations

For a fresh PostgreSQL installation, install/start Docker Desktop and run **start-postgresql.bat**. Existing PostgreSQL installations keep their current database URL, secrets and data; use `start.bat` for that mode. The production Compose deployment continues to use PostgreSQL.

To deliberately select a separate SQLite database in an existing installation, stop GymOS and run:

```powershell
py -3.12 scripts\configure.py --database sqlite --switch-database
.\start-sqlite.bat
```

The helper backs up the previous `.env` and leaves the PostgreSQL database untouched. **Switching backends does not copy existing records.** SQLite and PostgreSQL hold separate datasets; no automatic cross-database data migration is included. If you already have real PostgreSQL records, retain that database until you have planned and verified any transfer.

Keep the SQLite file on a writable local disk. SQLite serializes application transactions and suits a local installation; use PostgreSQL for a deployment requiring greater concurrent throughput. Do not put the live SQLite file in a shared network or cloud-sync folder.

## Addresses and stopping

| Service | Address |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://127.0.0.1:8000/api/v1 |
| Interactive API docs | http://127.0.0.1:8000/docs |
| Readiness and database mode | http://127.0.0.1:8000/health/ready |

Close the three application windows to stop the local app. SQLite needs no separate service shutdown. Re-running the launcher preserves configuration and database records. In PostgreSQL mode, `docker compose stop db` stops the database without removing its volume.

macOS/Linux: install Python 3.12 and Node.js 24, then run `bash scripts/start.sh sqlite`. PostgreSQL mode additionally requires Docker and uses `bash scripts/start.sh postgresql`.

## Documentation and tests

[Testing](docs/TESTING.md) · [Verification](docs/VERIFICATION.md) · [Architecture](docs/ARCHITECTURE.md) · [Feature status](docs/FEATURE_STATUS.md) · [Troubleshooting](docs/TROUBLESHOOTING.md) · [Deployment](docs/DEPLOYMENT.md)

Backend tests default to a new disposable SQLite database and do not use your local records. The source also includes a PostgreSQL test configuration, frontend tests, Playwright acceptance and CI configuration. This release is not a claim that Windows desktop execution, browser accessibility or production deployment has been independently certified.
