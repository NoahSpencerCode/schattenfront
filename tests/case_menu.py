"""The rebuilt main menu: one QUICK MATCH key in place of new/load,
the selection sheet with flags, dossiers, LOAD GAME bottom-left and
START GAME bottom-right, and the records page routing back to it."""
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

g = WW2RTSGame()                # boots straight to the menu
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


# --- THE FRONT PAGE: one key to a war, not two
texts = button_texts(g.menu)
check(any('QUICK MATCH' in t for t in texts),
      "QUICK MATCH stands on the front page")
check(not any('NEW GAME' in t for t in texts),
      "NEW GAME is retired")
check(not any('LOAD GAME' in t for t in texts),
      "LOAD GAME has left the front page")

# --- THE SELECTION SHEET
from config import PLAYABLE     # noqa: E402
g.menu.show_country_select()
for _ in range(5):
    g.taskMgr.step()
check(g.menu.sel_country == PLAYABLE[0],
      "the first power is pre-assigned (%s)" % g.menu.sel_country)
texts = button_texts(g.menu)
check(any('START GAME' in t for t in texts),
      "START GAME sits on the sheet")
check(any('LOAD GAME' in t for t in texts),
      "and LOAD GAME beside it")

from icons import flag_texture     # noqa: E402
# flag_texture hands back a PANDA path (forward slashes, a Windows
# drive as /c/) -- os.path.exists must be given the system's own
from panda3d.core import Filename as _Fn
missing = [k for k in PLAYABLE
           if not os.path.exists(_Fn(flag_texture(k)).toOsSpecific())]
check(not missing, "every power flies its standard (%s)" % missing)

from menu import COUNTRY_DOSSIERS     # noqa: E402
short = [k for k in PLAYABLE
         if len(COUNTRY_DOSSIERS[k]['strengths']) != 3
         or len(COUNTRY_DOSSIERS[k]['weaknesses']) != 3
         or len(COUNTRY_DOSSIERS[k]['ratings']) != 4]
check(not short, "every dossier is fully drafted (%s)" % short)

# --- PICKING A POWER re-prints the sheet with the new assignment
g.menu._select('soviet')
for _ in range(5):
    g.taskMgr.step()
check(g.menu.sel_country == 'soviet', "the pen moves to the Soviet row")

# --- START GAME hands the chosen power to the campaign
started = []
g.menu.on_start_game = lambda c: started.append(c)
g.menu._start()
check(started == ['soviet'],
      "START GAME opens the chosen command (%s)" % started)

# --- THE RECORDS PAGE routes back to the sheet it came from
g.menu.show_load_page('select')
for _ in range(5):
    g.taskMgr.step()
g.messenger.send('b')
for _ in range(5):
    g.taskMgr.step()
texts = button_texts(g.menu)
check(any('START GAME' in t for t in texts),
      "BACK from the records returns to the selection sheet")

finish()
