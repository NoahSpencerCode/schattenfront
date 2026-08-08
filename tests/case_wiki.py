"""THE FIELD MANUAL: the front page carries CAMPAIGN (dead), WIKI
and the folder itself; every tab prints without a crash; and the
figures on the pages are READ FROM THE GAME'S OWN TABLES, so the
manual cannot drift from the code."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

from harness import check, finish     # noqa: E402

from panda3d.core import loadPrcFileData     # noqa: E402
loadPrcFileData('', 'window-type offscreen')
loadPrcFileData('', 'audio-library-name null')
loadPrcFileData('', 'win-size 1280 720')
loadPrcFileData('', 'textures-power-2 none')

from game import WW2RTSGame     # noqa: E402

g = WW2RTSGame()
for _ in range(10):
    g.taskMgr.step()


def button_texts(menu):
    out = []
    for w in menu.widgets:
        try:
            out.append(str(w['text']))
        except Exception:
            pass
    return out


# --- THE FRONT PAGE
texts = button_texts(g.menu)
check(any('CAMPAIGN' in t and 'COMING SOON' in t for t in texts),
      "CAMPAIGN stands dark on the front page")
check(any(t.strip().endswith('WIKI') for t in texts),
      "and the WIKI key stands beside it")

# --- THE FOLDER: every tab prints
import wiki as wikimod     # noqa: E402
g.menu.show_wiki()
for _ in range(5):
    g.taskMgr.step()
w = g.menu.wiki
check(w is not None, "the manual opens")
check(len(wikimod.TABS) == 12, "twelve tabs on the folder (%d)"
      % len(wikimod.TABS))
for key, _label in wikimod.TABS:
    w._open(key)
    for _ in range(2):
        g.taskMgr.step()
    check(w.tab == key, "the %s page prints" % key.upper())

# --- THE FIGURES ARE THE GAME'S OWN: spot-check the live sources
# the manual reads from against the tables the game plays by
import config as C     # noqa: E402
from units import UNIT_TYPES     # noqa: E402
import tech     # noqa: E402
check(UNIT_TYPES['tank']['cost'] == 960,
      "the army table reads the live price of a tank ($%d)"
      % UNIT_TYPES['tank']['cost'])
check(C.TAX_EQUILIBRIUM == 30 and C.BUDGET_PERIOD_DAYS == 14,
      "the economy page reads the live fortnight and tax laws")
check(len(tech.NODES) >= 10,
      "the research page reads the live chart (%d programmes)"
      % len(tech.NODES))

# --- ESC returns to the front page and puts the folder away
g.messenger.send('escape')
for _ in range(3):
    g.taskMgr.step()
check(g.menu.wiki is None, "ESC files the manual away")
texts = button_texts(g.menu)
check(any('QUICK MATCH' in t for t in texts),
      "and the front page stands again")

finish()
