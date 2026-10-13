@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto missingpython
where npm >nul 2>nul
if errorlevel 1 goto missingnode
set "GYMOS_MODE=%~1"
if not defined GYMOS_MODE set "GYMOS_MODE=auto"
py -3.12 scripts\configure.py --database "%GYMOS_MODE%"
if errorlevel 1 goto failed
set "GYMOS_DB="
for /f "delims=" %%D in ('py -3.12 scripts\configure.py --show-database') do set "GYMOS_DB=%%D"
if "%GYMOS_DB%"=="postgresql" goto startpostgres
if not "%GYMOS_DB%"=="sqlite" goto failed
echo Using SQLite. No Docker or database server is required.
goto dependencies
:startpostgres
where docker >nul 2>nul
if errorlevel 1 goto missingdocker
docker compose up -d --wait db
if errorlevel 1 goto failed
:dependencies
echo Setting up Python dependencies...
if not exist backend\.venv\Scripts\python.exe py -3.12 -m venv backend\.venv
if errorlevel 1 goto failed
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 goto failed
pushd backend
.venv\Scripts\python.exe -m alembic upgrade head
if errorlevel 1 (popd & goto failed)
.venv\Scripts\python.exe -m app.seed
if errorlevel 1 (popd & goto failed)
popd
call npm ci --prefix frontend
if errorlevel 1 goto failed
start "GymOS API" /D "%CD%\backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log"
start "GymOS Notifications" /D "%CD%\backend" cmd /k ".venv\Scripts\python.exe -m app.jobs"
start "GymOS Frontend" /D "%CD%\frontend" cmd /k "npm run dev"
echo.
echo Open http://localhost:5173 after Vite reports ready.
echo Sign-in details are in .local-credentials.txt. Keep this file private.
echo Close the three application windows to stop.
if "%GYMOS_DB%"=="sqlite" echo SQLite records remain saved in the configured local database file.
if "%GYMOS_DB%"=="postgresql" echo Run docker compose stop db to stop PostgreSQL.
pause
exit /b 0
:missingdocker
echo PostgreSQL mode requires Docker Desktop. For SQLite use a fresh extraction and start.bat.
goto failed
:missingpython
echo Install Python 3.12 with the py launcher.
goto failed
:missingnode
echo Install Node.js 24 LTS, then reopen this window.
:failed
echo Setup failed. Read the error above and docs\TROUBLESHOOTING.md.
pause
exit /b 1
