"""
Player-adjustable settings, persisted as settings.json next to the
game.  Tiny and deterministic: load() returns the defaults merged with
whatever the file holds, save() writes the whole dict back.
"""

import json
import os
import sys

def user_data_dir():
    """A folder the player can always write to, whatever the game
    was installed into. A Windows install under Program Files is
    READ-ONLY to a standard user -- settings written beside the
    executable there are silently lost -- and the same is true of a
    translocated mac bundle."""
    name = 'Global Operations 1939'
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    elif sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = (os.environ.get('XDG_DATA_HOME')
                or os.path.expanduser('~/.local/share'))
    path = os.path.join(base, name)
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


# A frozen (shipped) build keeps the player's settings in his own
# data folder; run from source they sit beside the code, where a
# developer expects them.
if getattr(sys, 'frozen', False):
    SETTINGS_PATH = os.path.join(user_data_dir(), 'settings.json')
    _LEGACY_SETTINGS = os.path.abspath('settings.json')
else:
    SETTINGS_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'settings.json')
    _LEGACY_SETTINGS = None

DEFAULTS = {
    # MSAA sample count: 0 (off), 2, 4 or 8
    'antialias': 4,
}


def load_settings():
    settings = dict(DEFAULTS)
    for path in (SETTINGS_PATH, _LEGACY_SETTINGS):
        if not path:
            continue
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                settings.update(data)
            break               # the player's own file wins
        except Exception:
            continue            # missing/corrupt -> try the next
    return settings


def save_settings(settings):
    try:
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as fh:
            json.dump(settings, fh, indent=2, sort_keys=True)
    except Exception as exc:
        print("Could not save settings:", exc)
