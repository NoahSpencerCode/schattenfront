@echo off
REM Global Operations (1939 Edition) -- double-click launcher for Windows.
setlocal
cd /d "%~dp0"

REM `where python` also finds the Microsoft Store ALIAS STUB, which is
REM not an interpreter: probe by RUNNING one instead of locating it.
python -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo Python 3 is required. Install it from https://www.python.org
    echo ^(during setup, tick "Add python.exe to PATH"^).
    pause
    exit /b 1
)

REM The pinned wheels cover Python 3.9 to 3.12. A newer interpreter has
REM no matching panda3d/numpy build and pip would try to compile them.
python -c "import sys; sys.exit(0 if (3,9) <= sys.version_info[:2] <= (3,12) else 1)" >nul 2>nul
if errorlevel 1 (
    echo This game needs Python 3.9 - 3.12.
    python -c "import sys; print('You have', sys.version.split()[0])"
    echo Install 3.12 from https://www.python.org and try again.
    pause
    exit /b 1
)

if not exist venv\Scripts\python.exe (
    echo First run: preparing the war room ^(installing dependencies^)...
    python -m venv venv
    if errorlevel 1 (
        echo Could not create the virtual environment.
        pause
        exit /b 1
    )
    venv\Scripts\python -m pip install --upgrade pip
    venv\Scripts\python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed -- see the messages above.
        pause
        exit /b 1
    )
)

venv\Scripts\python main.py
if errorlevel 1 (
    echo.
    echo The game exited with an error -- see the messages above.
    pause
)
