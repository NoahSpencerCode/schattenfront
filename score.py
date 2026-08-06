"""
THE SCORE: the music that plays under the war, and the recorded
voices that cut across it.

Two programmes, one conductor:

  THE MENU stands on a single looping march -- ENGINES OF WAR --
  and at odd intervals a wireless set somewhere in the building
  carries a war leader's address OVER it. The march never stops for
  the speech; the speech is laid on top, the way a broadcast is
  heard across a room where a gramophone is playing.

  THE CAMPAIGN plays no music most of the time -- the map has its
  own quiet -- and then, at random, one of the pack's marches comes
  up, plays through, and leaves silence behind it again.

The files are the artist's own (media/WW2 Military Music Pack) and
the recordings are public-domain broadcasts (media/speeches). Every
path is resolved once at load; a missing file simply means that
piece is never heard, and never a crash.
"""

import os
import random

# the paths are RELATIVE, exactly as the menu's reel is: main.py
# makes the game root the working directory and the window machinery
# re-asserts it, which is what keeps a frozen bundle finding its own
# media (an absolute path taken from __file__ would not)
from config import MEDIA_PATH

PACK = os.path.join(MEDIA_PATH, 'WW2 Military Music Pack')
TRACKS = os.path.join(PACK, 'Tracks', 'ogg')
LOOPS = os.path.join(PACK, 'Loops', 'ogg')
SPEECHES = os.path.join(MEDIA_PATH, 'speeches')

# the march the main menu stands on
MENU_LOOP = '2. Engines of War (Loop).ogg'

# the recorded addresses, and how loud a wireless set carries
SPEECH_FILES = ('FDR_pearlharborspeech_64kb.mp3',)

MUSIC_VOLUME = 0.55
MENU_VOLUME = 0.60
SPEECH_VOLUME = 0.95

# how long the map stays quiet between marches, in seconds
CAMPAIGN_GAP = (150.0, 420.0)
# and how long the menu waits before a broadcast, and between them
SPEECH_GAP = (35.0, 110.0)


def _listing(folder, suffix='.ogg'):
    try:
        return sorted(os.path.join(folder, f)
                      for f in os.listdir(folder)
                      if f.lower().endswith(suffix))
    except OSError:
        return []


class Score:
    """Owns every piece of music and every recording. One instance
    lives on the game and is told when the menu opens, when the
    campaign begins, and once a frame."""

    def __init__(self, base):
        self.base = base
        self.mode = None            # 'menu' | 'campaign' | None
        self.music = None           # the piece now playing
        self.speech = None          # a recording laid over it
        self._next_track = 0.0      # seconds until the next piece
        self._next_speech = 0.0
        self.tracks = _listing(TRACKS)
        self.menu_loop = os.path.join(LOOPS, MENU_LOOP)
        if not os.path.exists(self.menu_loop):
            loops = _listing(LOOPS)
            self.menu_loop = loops[0] if loops else None
        self.speeches = [os.path.join(SPEECHES, f)
                         for f in SPEECH_FILES
                         if os.path.exists(os.path.join(SPEECHES, f))]
        self._rng = random.Random()

    # ---------------------------------------------------------- plumbing
    def _load(self, path, loop=False, volume=MUSIC_VOLUME):
        """A sound from the music manager, or None when the device or
        the file is missing. Music never shares the sfx manager: the
        interface keys must stay audible under it."""
        if not path or not os.path.exists(path):
            return None
        try:
            # THE FILENAMES CARRY SPACES AND LEADING DIGITS: Panda
            # wants its own path form, not the operating system's
            from panda3d.core import Filename
            snd = self.base.loader.loadMusic(
                Filename.fromOsSpecific(path))
            if snd is None:
                return None
            snd.setLoop(bool(loop))
            snd.setVolume(volume)
            return snd
        except Exception as exc:
            print("WARNING: could not load %s: %r"
                  % (os.path.basename(path), exc))
            return None

    def _stop(self, snd):
        try:
            if snd is not None:
                snd.stop()
        except Exception:
            pass

    def _playing(self, snd):
        try:
            from panda3d.core import AudioSound
            return (snd is not None
                    and snd.status() == AudioSound.PLAYING)
        except Exception:
            return False

    # ------------------------------------------------------------ states
    def enter_menu(self):
        """The main menu: ENGINES OF WAR, looping, and a broadcast
        laid over it now and then."""
        if self.mode == 'menu':
            return
        self.stop()
        self.mode = 'menu'
        self.music = self._load(self.menu_loop, loop=True,
                                volume=MENU_VOLUME)
        if self.music is not None:
            self.music.play()
        self._next_speech = self._rng.uniform(*SPEECH_GAP)

    def enter_campaign(self):
        """The map: quiet, until a march comes up of its own accord."""
        if self.mode == 'campaign':
            return
        self.stop()
        self.mode = 'campaign'
        # the first march waits a while: the opening despatches
        # should be read in silence
        self._next_track = self._rng.uniform(*CAMPAIGN_GAP)

    def stop(self):
        self._stop(self.music)
        self._stop(self.speech)
        self.music = self.speech = None
        self.mode = None

    # ------------------------------------------------------------- update
    def update(self, dt):
        if self.mode == 'menu':
            self._tick_menu(dt)
        elif self.mode == 'campaign':
            self._tick_campaign(dt)

    def _tick_menu(self, dt):
        # the march is looping on its own; only the broadcast is
        # timed. It plays OVER the music -- nothing is stopped.
        if not self.speeches:
            return
        if self._playing(self.speech):
            return
        self._next_speech -= dt
        if self._next_speech > 0:
            return
        self._next_speech = self._rng.uniform(*SPEECH_GAP)
        self.speech = self._load(self._rng.choice(self.speeches),
                                 loop=False, volume=SPEECH_VOLUME)
        if self.speech is not None:
            self.speech.play()

    def _tick_campaign(self, dt):
        if not self.tracks:
            return
        if self._playing(self.music):
            return                  # a march is running its course
        self._next_track -= dt
        if self._next_track > 0:
            return
        self._next_track = self._rng.uniform(*CAMPAIGN_GAP)
        # never the same march twice running, when there is a choice
        pool = [t for t in self.tracks if t != getattr(
            self, '_last_track', None)] or self.tracks
        path = self._rng.choice(pool)
        self._last_track = path
        self.music = self._load(path, loop=False,
                                volume=MUSIC_VOLUME)
        if self.music is not None:
            self.music.play()
