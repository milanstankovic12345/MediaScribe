@echo off
cd /d "%~dp0"
if not exist .venv (
    python -m venv .venv || goto :err
)
rem Re-check every launch so packages added to requirements.txt later get installed.
.venv\Scripts\python -m pip install -q --disable-pip-version-check -r requirements.txt || goto :err
.venv\Scripts\python main.py
exit /b 0
:err
echo Setup failed.
pause
