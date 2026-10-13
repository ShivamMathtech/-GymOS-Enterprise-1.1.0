# Troubleshooting

| Symptom | Action |
|---|---|
| `py` or Python 3.12 missing | Install Python 3.12 with the launcher, reopen terminal, run `py -0p`. |
| `npm` not found | Install Node.js 24 LTS and reopen terminal. |
| PowerShell blocks npm.ps1 | Use Command Prompt or run `npm.cmd`; no machine-wide execution-policy change is required. |
| Docker daemon unavailable | Start Docker Desktop and wait for the engine. Confirm WSL 2 setup. |
| Docker requires virtualization | Enable virtualization in firmware and required Windows features following Docker's installation guide. |
| 5432 already in use | Stop the other local PostgreSQL or change root `.env` POSTGRES_PORT and the port in backend DATABASE_URL to the same unused port, then restart Compose. |
| 5173 / 8000 already in use | Close old GymOS terminals. For a deliberate API-port change, update Vite's proxy target as well. |
| Database authentication failed after changing password | Existing Docker volumes retain their database user's original password. Change the actual database password through authorized SQL; editing .env alone does not change it. Never delete a live volume as a shortcut. |
| Missing `DATABASE_URL` / `SECRET_KEY` | Use 1.1.0 and run `start-sqlite.bat` from a fresh extraction, or `py -3.12 scripts/configure.py --database sqlite` from the project root. Setup fills missing fields and generates a private secret. |
| Partial configuration from 1.0.0 | The 1.1.0 configuration helper can fill missing fields. SQLite needs only backend/.env and no root PostgreSQL configuration. Existing valid secrets are preserved. |
| Existing PostgreSQL mode when requesting SQLite | Stop GymOS and explicitly run `py -3.12 scripts/configure.py --database sqlite --switch-database`. This preserves the old configuration but does not transfer database records. |
| SQLite database busy | Let the current operation finish and retry the unchanged form. Close external database editors holding write transactions. Keep the live database on a local disk. |
| SQLite unable to open database | Use a writable extraction folder; do not run inside the ZIP viewer or from a protected installation directory. Relative paths resolve inside backend. |
| Settings differ from backend/.env | Environment variables override the file. In PowerShell, inspect only variable names and remove obsolete DATABASE_URL / SECRET_KEY overrides before setup. |
| Missing tables / readiness 503 | From backend run `.venv\Scripts\python.exe -m alembic upgrade head`; verify DB is healthy. |
| Login says invalid organization | Use the organization slug (demo-gym), not its display name. Read `.local-credentials.txt` for the exact generated password. |
| Login cookies keep disappearing | Use http://localhost:5173 consistently. Keep VITE_API_BASE=/api/v1. Development COOKIE_SECURE must be false; production must be HTTPS + true. |
| 403 on a staff action | Verify assigned role and branch. Receptionists cannot edit private notes, refund, export members or view private progress. |
| 429 during local testing | Auth endpoints limit attempts per IP and route for 15 minutes. Wait for expiry; do not disable production protection. |
| Check-in rejected | Check active profile, full invoice payment, start/end dates, freeze/grace, branch and hours. Check out an already open visit first. |
| Refund rejected | Total refunds cannot exceed the original payment. A refund is an explicit record, never a deletion. |
| Booking rejected | Assign the trainer to the client, issue a package, check balance, availability and conflicting sessions. |
| Reminders absent | Keep the `python -m app.jobs` terminal running. Notifications are in-app; scheduled SMTP/SMS delivery is not implemented. |
| Reset email absent in development | When SMTP is missing/fails, inspect backend/var/dev-outbox privately for the one-time link. Reset API never exposes it. Do not publish that directory. |
| Staff invite email absent | Owner UI returns a one-time activation link when delivery is unavailable. Share it through an authorized secure channel. No messages are sent automatically by this ZIP. |
| Frontend dependencies fail | Check network/proxy configuration and use `npm ci`. Do not copy node_modules from another operating system. |
| Missing Windows time zone data | Reinstall backend requirements; tzdata is included for Windows zoneinfo support. |
| Browser blocks receipt popup | Permit popups for local GymOS or use the downloaded receipt.html. Print it from the browser to save PDF. |

The API returns an `X-Request-ID` header and error request ID. Search structured server logs for this ID. Logs intentionally omit request bodies, query strings, credentials and member contact details.
