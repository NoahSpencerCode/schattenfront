#!/bin/bash
# Zero Hour: 1939 — double-click launcher for macOS.
# First run creates a local Python environment and installs dependencies,
# then starts the game. Later runs start immediately.

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required. Install it from https://www.python.org"
    read -r -p "Press ENTER to close..."
    exit 1
fi

if [ ! -x "venv/bin/python" ]; then
    echo "First run: preparing the war room (installing dependencies)..."
    python3 -m venv venv || exit 1
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt || exit 1
fi

exec ./venv/bin/python main.py
