"""Headless test harness: boots the real game offscreen and steps
the real task manager. Every case file drives actual handlers --
nothing is mocked.

Usage in a case:
    from harness import boot, step, until, PASS, FAIL, finish
    g = boot('germany')
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

_checks = {'pass': 0, 'fail': 0}


def boot(country='germany', ai=False, size=(800, 600)):
    from panda3d.core import loadPrcFileData
    loadPrcFileData('', 'window-type offscreen')
    loadPrcFileData('', 'audio-library-name null')
    loadPrcFileData('', 'win-size %d %d' % size)
    loadPrcFileData('', 'textures-power-2 none')
    from game import WW2RTSGame
    g = WW2RTSGame()
    g.start_game(country)
    if not ai:
        g._nation_ais = {}      # a still world unless the case wants one
    t0 = time.time()
    while getattr(g, '_loading_np', None) is not None \
            and time.time() - t0 < 90:
        step(g, 10)
    step(g, 30)                 # settle the first frames
    return g


def step(g, n=1):
    for _ in range(n):
        g.taskMgr.step()


def until(g, cond, timeout_s=240, label='condition'):
    """Step the sim until cond() or the wall clock runs out.
    Returns True when the condition was met."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if cond():
            return True
        step(g, 12)
    print("TIMEOUT waiting for %s" % label)
    return False


def check(ok, label):
    if ok:
        _checks['pass'] += 1
        print("PASS %s" % label)
    else:
        _checks['fail'] += 1
        print("FAIL %s" % label)


def finish():
    print("---- %d passed, %d failed" %
          (_checks['pass'], _checks['fail']))
    sys.exit(1 if _checks['fail'] else 0)
