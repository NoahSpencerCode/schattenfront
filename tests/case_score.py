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
check(any('Eisenhower' in s for s in sc.speeches),
      "Eisenhower's D-Day order is on the shelf")
check(not os.path.isabs(sc.menu_loop),
      "media paths stay RELATIVE, as a frozen bundle needs")

# --- THE MENU: the march plays, and the wireless drifts over it
sc.enter_menu()
check(sc.mode == 'menu' and sc.music is not None,
      "the menu march is up")
march = sc.music

from score import (SPEECH_GAP, SPEECH_SEGMENT, SPEECH_FADE,
                   SPEECH_VOLUME)
lo, hi = SPEECH_GAP
check(lo == 10.0 and hi == 30.0,
      "the dial rests ten to thirty seconds between broadcasts")
check(SPEECH_SEGMENT == 20.0, "and holds each one twenty seconds")
waits = []
for _ in range(40):
    sc.enter_campaign()             # force a fresh menu each time
    sc.enter_menu()
    waits.append(sc._next_speech)
check(all(lo <= w <= hi for w in waits),
      "every fresh menu schedules inside that window "
      "(%.1f to %.1f)" % (min(waits), max(waits)))

sc.enter_campaign()
sc.enter_menu()
sc._next_speech = 0.0
sc.update(0.1)
check(sc.speech is not None, "a broadcast comes over the wireless")
check(sc.music is march or sc.music is not None,
      "AND THE MARCH NEVER STOPS FOR IT -- still playing")

# --- THE ENVELOPE: rise, hold, die away -- the march untouched
sc.update(0.5)                      # half a second in: fading up
early = sc._speech_vol
check(0.0 < early < SPEECH_VOLUME * 0.5,
      "the voice FADES IN (%.2f of %.2f half a second in)"
      % (early, SPEECH_VOLUME))
sc.update(SPEECH_FADE)              # past the head fade: full voice
check(abs(sc._speech_vol - SPEECH_VOLUME) < 1e-6,
      "holds at full voice through the middle (%.2f)"
      % sc._speech_vol)
sc._speech_t = sc._speech_seg - 1.0
sc.update(0.05)                     # a second from the end: dying
check(sc._speech_vol < SPEECH_VOLUME * 0.5,
      "and FADES OUT toward the end (%.2f)" % sc._speech_vol)
check(sc.music is not None, "the march plays through all of it")
sc.update(2.0)                      # past the segment: put down
check(sc.speech is None,
      "at twenty seconds the broadcast is put down")
check(lo <= sc._next_speech <= hi,
      "and the dial rests 10-30s before the next (%.1fs)"
      % sc._next_speech)

# --- the addresses take turns: never the same one twice running
heard = set()
for _ in range(8):
    sc._next_speech = 0.0
    sc.update(0.1)                  # a broadcast comes on
    heard.add(sc._last_speech)
    sc._speech_t = 99.0
    sc.update(0.1)                  # and is put down
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
check(g.score._last_speech in g.score.speeches,
      "and it is one of the addresses on the shelf")
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

# --- THE AUDIO WATCH: headphones plugged mid-session move the
# system's default output; the game follows by rebuilding its
# managers. Under the null audio device the WATCH never engages
# (nothing real to follow) but the rebuild path must hold.
check(not g.taskMgr.getTasksNamed('audio_watch'),
      "the watch stays off the null audio device")
g.show_menu()
mode_before = g.score.mode
g.restart_audio()
check(g.score.mode == mode_before,
      "restart_audio keeps the programme (%s)" % g.score.mode)
check(g.click_snd is not None and g.fax_snd is not None,
      "and the interface sounds are rewired")
g.score.enter_campaign()
g.restart_audio()
check(g.score.mode == 'campaign',
      "the campaign's quiet survives the swap too")

# --- a missing shelf is silence, never a crash
sc.tracks = []
sc.speeches = []
sc.music = None
sc._next_track = 0.0
sc.update(0.1)
check(sc.music is None, "no music, no crash")

finish()
