#!/usr/bin/env python3
"""
Schattenfront — a real-time strategy game on a 3D globe.
Run:  python main.py   (see README.md for setup)
"""

import os
import sys

# Run from the game directory so relative asset paths work when the
# launcher is double-clicked from elsewhere.
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

from game import WW2RTSGame


def main():
    game = WW2RTSGame()
    game.run()


if __name__ == '__main__':
    main()
