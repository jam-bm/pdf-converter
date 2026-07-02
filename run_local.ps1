# run_local.ps1 — start the PDF Converter backend on Windows with no Docker/Postgres/Redis.
#
# Uses SQLite for the database and runs Celery conversion tasks inline (eager mode), so
# only Python + LibreOffice are needed. Config comes from the local .env file.
#
# Usage (from the pdf-converter/ folder):
#   ./run_local.ps1
#
# First run creates a Python 3.13 virtualenv in .venv-local and installs deps. The API
# then listens on http://0.0.0.0:8000 — reachable from the Flutter app as:
#   Android emulator -> http://10.0.2.2:8000   (the app's default)
#   iOS simulator    -> http://localhost:8000
#   Real device      -> http://<this-PC's-LAN-IP>:8000

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv-local\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating Python 3.13 virtualenv (.venv-local)..." -ForegroundColor Cyan
    py -3.13 -m venv .venv-local
    & $venvPython -m pip install --upgrade pip
    Write-Host "Installing backend dependencies (requirements-local.txt)..." -ForegroundColor Cyan
    & $venvPython -m pip install -r requirements-local.txt
}

if (-not (Test-Path (Join-Path $PSScriptRoot ".env"))) {
    Write-Warning ".env not found — the app expects SQLite/eager settings there. See .env.example."
}

Write-Host "Starting API on http://0.0.0.0:8000 (Ctrl+C to stop)..." -ForegroundColor Green
& $venvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
