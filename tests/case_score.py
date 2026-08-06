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
check(len(sc.speeches) >= 1, "the recorded address is on file")
check(any('FDR' in s for s in sc.speeches), "the FDR address")
check(not os.path.isabs(sc.menu_loop),
      "media paths stay RELATIVE, as a frozen bundle needs")

# --- THE MENU: the march plays, and a broadcast is laid OVER it
sc.enter_menu()
check(sc.mode == 'menu' and sc.music is not None,
      "the menu march is up")
march = sc.music
sc._next_speech = 0.0
sc.update(0.1)
check(sc.speech is not None, "a broadcast comes over the wireless")
check(sc.music is march,
      "AND THE MARCH NEVER STOPS FOR IT -- same piece still playing")

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
