"""
Player-adjustable settings, persisted as settings.json next to the
game.  Tiny and deterministic: load() returns the defaults merged with
whatever the file holds, save() writes the whole dict back.
"""

import json
import os
import sys

# A frozen (shipped) build has no source directory: the settings live
# in the game folder, which main.py makes the working directory.
if getattr(sys, 'frozen', False):
    SETTINGS_PATH = os.path.abspath('settings.json')
else:
    SETTINGS_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'settings.json')

DEFAULTS = {
    # MSAA sample count: 0 (off), 2, 4 or 8
    'antialias': 4,
}


def load_settings():
    settings = dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            settings.update(data)
    except Exception:
        pass                        # missing/corrupt file -> defaults
    return settings


def save_settings(settings):
    try:
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as fh:
            json.dump(settings, fh, indent=2, sort_keys=True)
    except Exception as exc:
        print("Could not save settings:", exc)
