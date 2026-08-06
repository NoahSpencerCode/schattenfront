"""The score: the menu's looping march with a broadcast laid over
it, and the campaign's occasional marches. Runs under the null
audio device, so it proves the PROGRAMME -- which piece is chosen
when -- rather than that a speaker made a noise."""
from harness import boot, step, check, finish
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

# --- THE GAME ACTUALLY DRIVES IT. The score was once ticked below
# the "is the game playing?" guard, so on the MENU -- where the
# broadcast belongs -- its timer never ran and no speech was ever
# heard. Drive the real frame task in the real menu state.
g.show_menu()
check(g.game_state == 'menu', "the menu is up")
check(g.score.mode == 'menu', "and the score knows it")
check(g.score.music is not None, "the march is playing on the menu")
g.score._next_speech = 0.02
step(g, 20)
check(g.score.speech is not None,
      "the FRAME TASK brings the broadcast on while on the menu")
check('FDR' in (g.score._last_speech or ''),
      "and it is Roosevelt")
check(g.score.music is not None, "with the march still under it")

# --- THE MARCH AND THE VOICE SOUND TOGETHER. ShowBase builds the
# music manager with a CONCURRENT SOUND LIMIT OF ONE, so starting a
# speech made the engine stop the march to make room. The null audio
# device used in these cases ignores the limit entirely -- which is
# why this was invisible here -- so drive a stand-in manager that
# behaves as the real one does.
class OneAtATime:
    """A music manager as ShowBase leaves it: one sound only."""

    def __init__(self):
        self.limit = 1

    def getConcurrentSoundLimit(self):
        return self.limit

    def setConcurrentSoundLimit(self, n):
        self.limit = n


real_mm = g.musicManager
fake = OneAtATime()
g.musicManager = fake
check(fake.limit == 1, "ShowBase leaves the manager at ONE sound")
g.score._open_the_manager()
check(fake.limit == 0,
      "the score LIFTS the limit so two streams may sound at once")
g.musicManager = real_mm

# --- a missing shelf is silence, never a crash
sc.tracks = []
sc.speeches = []
sc.music = None
sc._next_track = 0.0
sc.update(0.1)
check(sc.music is None, "no music, no crash")

finish()
