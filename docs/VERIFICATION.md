# Verification record: 1.1.0

Checks performed on October 13, 2026, on Linux using Python 3.12.14 and Node.js 24.19.0. These are executed checks, separate from the supplied CI and manual setup instructions.

| Check | Observed result |
|---|---|
| Real SQLite backend test suite | **30 passed, zero skipped.** Includes the existing 20 tests and 10 new SQLite/configuration checks. |
| Concurrent requests on SQLite | Duplicate payment requests produced one payment; competing check-ins produced one open visit. Both tests passed. |
| SQLite money storage | Fractional payments and the maximum supported invoice value retained exact totals; direct queries confirmed integer minor-unit storage. |
| SQLite dates and constraints | UTC timestamps, foreign keys, tenant composite keys, immutable payment triggers and the partial attendance index passed their checks. |
| SQLite configuration | Fresh, empty, placeholder and partial configurations were exercised. Repeated setup preserved secrets. Paths with spaces and loading from another working directory were checked. Explicit backend switching preserved the old configuration. |
| Clean-install smoke test | A clean copy generated configuration, migrated SQLite, seeded the demo account and started a real Uvicorn process. HTTP login, member creation, membership assignment, payment, attendance, reports and a jobs pass succeeded. After restarting the API process, the member and paid invoice remained available. |
| SQLite backup and restore | Live backup, restore into a new file, integrity checks, a fresh Python-process read and refusal to overwrite an existing restore target passed. |
| SQLite migrations | Upgrade, schema drift check, downgrade on an empty disposable database, re-upgrade and another drift check passed. |
| PostgreSQL compatibility regression | **22 passed, 8 skipped** through PGlite's PostgreSQL engine/socket adapter. Five skips are SQLite-only checks; three are the native PostgreSQL checks described below. |
| PostgreSQL schema compatibility | `alembic check` found no schema drift against the existing 1.0.0 PostgreSQL schema. The new SQLite type variants do not change PostgreSQL column types. |
| Frontend | **8 tests passed**; TypeScript checking and the Vite production build passed. |
| Python quality | Ruff formatting and lint checks passed for the backend and helper scripts. |

The test runner emits one non-failing warning about Starlette's HTTPX TestClient deprecation. The tests still pass. The Python and npm dependency locks are unchanged apart from the frontend application version. The earlier October 12 runtime audits reported no known vulnerabilities; this is a point-in-time result, not a security certification.

## Checks still requiring the target environment

- Actual Windows `start-sqlite.bat` / `start.bat` execution and Windows dependency installation. The launcher is supplied and inspected; Linux testing is not Windows execution.
- Native PostgreSQL concurrency and immutable-trigger rollback. PGlite is useful for PostgreSQL query compatibility, but its socket multiplexer does not establish native locking behavior.
- Browser Playwright acceptance, a complete visual/accessibility review and real SMTP delivery.
- Production Docker images, HTTPS rollout, PostgreSQL backup/restore, load tests and an independent security review.

SQLite backup/restore and concurrent transaction checks **were** exercised in this release. SQLite storage serializes application transactions; the tests do not claim high-concurrency enterprise capacity.

## Scope and archive

All existing business modules use the configured database. Switching from PostgreSQL to SQLite selects a separate dataset and does not migrate old records automatically. Broader feature limits remain listed in `FEATURE_STATUS.md`.

The source archive includes code, dependency locks, migrations, tests, launchers, example configuration, OpenAPI and documentation. It excludes actual secrets, database records, uploads, credentials, installed dependencies and caches. On first setup, configuration and a local SQLite database are generated for that installation.
