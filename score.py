"""
THE SCORE: the music that plays under the war, and the recorded
voices that cut across it.

Two programmes, one conductor:

  THE MENU stands on a single looping march -- ENGINES OF WAR --
  and a wireless set somewhere in the building drifts across the
  dial: every ten to thirty seconds it finds a war leader's address
  ALREADY IN PROGRESS at some random point, fades it in, holds it
  twenty seconds, and fades it away again. The march never stops
  for the voice and its volume is never touched; the broadcast is
  laid on top, the way a wireless is heard across a room where a
  gramophone is playing.

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

# THE RECORDED ADDRESSES on the shelf. Any of them may come over
# the wireless; the same one is never heard twice running.
SPEECH_FILES = ('FDR_pearlharborspeech_64kb.mp3',
                'Gen._Dwight_D._Eisenhower_s_D-Day_order_of_the_day'
                '.mp3')

MUSIC_VOLUME = 0.55
MENU_VOLUME = 0.60
SPEECH_VOLUME = 0.76

# how long the map stays quiet between marches, in seconds
CAMPAIGN_GAP = (150.0, 420.0)
# THE WIRELESS ON THE MENU: a broadcast is caught mid-speech at a
# random point, faded in, held for the segment, faded out, and the
# dial rests ten to thirty seconds before finding another
SPEECH_GAP = (10.0, 30.0)
SPEECH_SEGMENT = 20.0
SPEECH_FADE = 5.0


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
        self._open_the_manager()

    def _open_the_manager(self):
        """THE MARCH AND THE VOICE MUST SOUND TOGETHER.

        ShowBase builds the music manager with a CONCURRENT SOUND
        LIMIT OF ONE -- 'ensure only 1 midi song is playing at a
        time' -- so the moment a speech began, the engine stopped
        the march to make room for it. Lift the limit: this score
        deliberately wants two streams at once, and nothing else
        goes through this manager."""
        try:
            mm = getattr(self.base, 'musicManager', None)
            if mm is not None and mm.getConcurrentSoundLimit() != 0:
                mm.setConcurrentSoundLimit(0)       # 0 = no limit
        except Exception as exc:
            print("WARNING: could not free the music manager: %r"
                  % exc)

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
        # the wireless rests before finding its first broadcast,
        # the same ten-to-thirty beat it keeps thereafter
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
        # timed. It plays OVER the music -- nothing is stopped and
        # the march's volume is never touched; the fades below are
        # the SPEECH'S alone.
        if not self.speeches:
            return
        if self.speech is not None:
            # a broadcast is on: run its envelope -- rise, hold,
            # die away -- and put it down when the segment is done
            self._speech_t += dt
            seg = self._speech_seg
            if self._speech_t >= seg:
                self._stop(self.speech)
                self.speech = None
                self._next_speech = self._rng.uniform(*SPEECH_GAP)
                return
            t = self._speech_t
            head = min(1.0, t / SPEECH_FADE)
            tail = min(1.0, (seg - t) / SPEECH_FADE)
            self._speech_vol = SPEECH_VOLUME * max(
                0.0, min(head, tail))
            try:
                self.speech.setVolume(self._speech_vol)
            except Exception:
                pass
            return
        self._next_speech -= dt
        if self._next_speech > 0:
            return
        # the dial finds a broadcast: any address but the one just
        # heard, joined ALREADY IN PROGRESS at a random point
        pool = [s for s in self.speeches
                if s != getattr(self, '_last_speech', None)] \
            or self.speeches
        path = self._rng.choice(pool)
        self._last_speech = path
        snd = self._load(path, loop=False, volume=0.0)
        if snd is None:
            self._next_speech = self._rng.uniform(*SPEECH_GAP)
            return
        try:
            length = float(snd.length())
        except Exception:
            length = 0.0
        # the segment fits inside the recording; a short recording
        # simply plays from its start
        seg = (min(SPEECH_SEGMENT, length) if length > 0.0
               else SPEECH_SEGMENT)
        start = 0.0
        if length > seg + 1.0:
            start = self._rng.uniform(0.0, length - seg - 1.0)
        self._speech_seg = seg
        self._speech_t = 0.0
        self._speech_vol = 0.0
        self._speech_start = start
        self.speech = snd
        # ON OPENAL THE SEEK MUST COME FIRST: setTime() does not
        # move a sound already playing -- it only arms the start
        # offset for the NEXT play(). (The menu reel's
        # play-then-setTime pattern is a MovieTexture rule; audio
        # is the other way round. Verified against the real
        # backend: seek-then-play lands on the mark, the reverse
        # plays from the top.)
        if start > 0.0:
            try:
                snd.setTime(start)
            except Exception:
                pass
        snd.play()

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
