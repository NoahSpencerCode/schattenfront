@echo off
REM Schattenfront — double-click launcher for Windows.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python 3 is required. Install it from https://www.python.org
    pause
    exit /b 1
)

if not exist venv\Scripts\python.exe (
    echo First run: preparing the war room ^(installing dependencies^)...
    python -m venv venv
    venv\Scripts\python -m pip install --upgrade pip
    venv\Scripts\pip install -r requirements.txt
)

venv\Scripts\python main.py
