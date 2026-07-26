#!/usr/bin/env python3
"""
Schattenfront — a real-time strategy game on a 3D globe.
Run:  python main.py   (see README.md for setup)
"""

import os
import sys

# Run from the game directory so relative asset paths work when the
# launcher is double-clicked from elsewhere. A FROZEN build (the
# shipped .app/.exe) anchors on the executable instead: game data
# sits beside the binary, or in Resources inside a mac bundle.
if getattr(sys, 'frozen', False):
    _base = os.path.dirname(os.path.abspath(sys.executable))
    for _cand in (_base, os.path.join(os.path.dirname(_base),
                                      'Resources')):
        if os.path.isdir(os.path.join(_cand, 'assets')):
            os.chdir(_cand)
            break
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

from panda3d.core import loadPrcFileData

from config import (SCREEN_WIDTH, SCREEN_HEIGHT, FULLSCREEN, WINDOW_TITLE,
                    SHOW_FPS_METER)

loadPrcFileData('', 'window-title %s' % WINDOW_TITLE)
loadPrcFileData('', 'win-size %d %d' % (SCREEN_WIDTH, SCREEN_HEIGHT))
loadPrcFileData('', 'fullscreen %s' % ('1' if FULLSCREEN else '0'))
loadPrcFileData('', 'sync-video 1')
loadPrcFileData('', 'text-flatten 1')
# keep non-power-of-two textures at full resolution (detail overlay)
loadPrcFileData('', 'textures-power-2 none')
# interface audio: console-key clicks and the FAX teletype
loadPrcFileData('', 'audio-library-name p3openal_audio')

# anti-aliasing must be requested before the window opens (the
# settings menu can also rebuild the window at runtime)
from settings import load_settings
_aa = int(load_settings().get('antialias', 0))
if _aa > 0:
    loadPrcFileData('', 'framebuffer-multisample 1')
    loadPrcFileData('', 'multisamples %d' % _aa)
if SHOW_FPS_METER:
    loadPrcFileData('', 'show-frame-rate-meter 1')

if '--offscreen' in sys.argv:
    # Headless smoke-test mode used by developers / CI.
    loadPrcFileData('', 'window-type offscreen')

if getattr(sys, 'frozen', False):
    # surface the TRUE cause of a numpy import failure in the field
    try:
        import numpy                                    # noqa: F401
    except ImportError as _e:
        import traceback
        print("numpy import failed; underlying cause:", file=sys.stderr)
        cause = _e.__cause__ or _e
        traceback.print_exception(type(cause), cause,
                                  cause.__traceback__)
        sys.exit(1)

from game import WW2RTSGame


def main():
    game = WW2RTSGame()
    game.run()


if __name__ == '__main__':
    main()
