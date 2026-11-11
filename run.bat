@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    rem Prefer the py launcher: a bare "python" may be the Microsoft Store alias.
    py -3 -m venv .venv || python -m venv .venv || goto :err
)
rem Re-check every launch so packages added to requirements.txt later get installed.
.venv\Scripts\python -m pip install -q --disable-pip-version-check -r requirements.txt || goto :err
.venv\Scripts\python main.py
exit /b 0
:err
echo Setup failed.
pause
