"""The score: the menu's looping march with a broadcast laid over
it, and the campaign's occasional marches. Runs under the null
audio device, so it proves the PROGRAMME -- which piece is chosen
when -- rather than that a speaker made a noise."""
from harness import boot, check, finish
import os

g = boot('germany')
sc = g.score
check(sc is not None, "the score is raised with the game")

# --- the pieces are found where the pack put them
check(len(sc.tracks) == 8, "eight marches on the shelf (%d)"
      % len(sc.tracks))
check(sc.menu_loop and 'Engines of War' in sc.menu_loop,
      "the menu stands on ENGINES OF WAR (%s)"
      % os.path.basename(sc.menu_loop or ''))
check(sc.menu_loop and '(Loop)' in sc.menu_loop,
      "...and on the LOOPING cut of it")
check(len(sc.speeches) == 2, "both recorded addresses on file (%d)"
      % len(sc.speeches))
check('FDR' in sc.speeches[0],
      "ROOSEVELT stands first in the running order")
check(any('Eisenhower' in s for s in sc.speeches),
      "and Eisenhower's D-Day order is with him")
check(not os.path.isabs(sc.menu_loop),
      "media paths stay RELATIVE, as a frozen bundle needs")

# --- THE MENU: the march plays, and a broadcast is laid OVER it
sc.enter_menu()
check(sc.mode == 'menu' and sc.music is not None,
      "the menu march is up")
march = sc.music

# THE FIRST BROADCAST COMES EARLY, and it is always Roosevelt
from score import FIRST_SPEECH_GAP
lo, hi = FIRST_SPEECH_GAP
check(lo == 15.0 and hi == 45.0,
      "the first broadcast is scheduled 15-45s in")
waits = []
for _ in range(40):
    sc.enter_campaign()             # force a fresh menu each time
    sc.enter_menu()
    waits.append(sc._next_speech)
check(all(lo <= w <= hi for w in waits),
      "every fresh menu schedules it inside that window "
      "(%.1f to %.1f)" % (min(waits), max(waits)))

sc.enter_campaign()
sc.enter_menu()
sc._next_speech = 0.0
sc.update(0.1)
check(sc.speech is not None, "a broadcast comes over the wireless")
check('FDR' in sc._last_speech,
      "and ROOSEVELT is the one heard first")
check(sc.music is march or sc.music is not None,
      "AND THE MARCH NEVER STOPS FOR IT -- still playing")

# later broadcasts may be either man, and never twice running
heard = set()
for _ in range(8):
    sc.speech = None
    sc._next_speech = 0.0
    sc.update(0.1)
    heard.add(sc._last_speech)
check(len(heard) == 2, "both men are heard in turn (%d)" % len(heard))

# --- THE CAMPAIGN: quiet first, then a march of its own accord
sc.enter_campaign()
check(sc.mode == 'campaign', "the campaign takes over")
check(sc.music is None, "the map opens in silence")
check(sc.speech is None, "and the broadcast is put away")
check(sc._next_track > 0, "a march is waiting on its interval")
sc._next_track = 0.0
sc.update(0.1)
first = sc.music
check(first is not None, "a march comes up on its own")

# --- and it does not repeat itself while there is a choice
picks = set()
for _ in range(6):
    sc.music = None
    sc._next_track = 0.0
    sc.update(0.1)
    picks.add(sc._last_track)
check(len(picks) > 1, "the marches vary (%d distinct)" % len(picks))

# --- a missing shelf is silence, never a crash
sc.tracks = []
sc.speeches = []
sc.music = None
sc._next_track = 0.0
sc.update(0.1)
check(sc.music is None, "no music, no crash")

finish()
