"""
Synthesised interface audio -- generated once into assets/audio, like
the pictograms: a mechanical button CLICK and the FAX teletype burst.
Bump AUDIO_VERSION to regenerate after changing a recipe.
"""

import os
import wave

import numpy as np

AUDIO_VERSION = 2
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "assets", "audio")
RATE = 22050


def _write(path, data):
    data = np.clip(data, -1.0, 1.0)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((data * 32767.0).astype("<i2").tobytes())


def _click():
    """A switch under a thumb: short damped knock with a bright tick."""
    n = int(RATE * 0.05)
    t = np.arange(n) / RATE
    rng = np.random.RandomState(7)
    body = np.sin(2 * np.pi * 640.0 * t) * np.exp(-t * 160.0)
    tick = np.sin(2 * np.pi * 2100.0 * t) * np.exp(-t * 420.0) * 0.5
    grit = rng.uniform(-1, 1, n) * np.exp(-t * 500.0) * 0.25
    return (body + tick + grit) * 0.7


def _fax():
    """A clerk at the keys: irregular typing -- quick bursts, small
    hesitations, every strike its own pitch -- then the margin bell."""
    rng = np.random.RandomState(23)
    dur = 0.72
    n = int(RATE * dur)
    out = np.zeros(n)
    t_all = np.arange(n) / RATE
    at = 0.015
    base = 1900.0
    strikes = 0
    while at < 0.52 and strikes < 16:
        i0 = int(at * RATE)
        m = int(RATE * rng.uniform(0.009, 0.014))
        if i0 + m >= n:
            break
        tt = np.arange(m) / RATE
        base *= rng.uniform(0.97, 1.03)          # the platen drifts
        f = base * rng.uniform(0.82, 1.22)       # each key its own voice
        hit = (np.sin(2 * np.pi * f * tt) * 0.55
               + rng.uniform(-1, 1, m) * 0.45) \
            * np.exp(-tt * rng.uniform(550.0, 850.0))
        out[i0:i0 + m] += hit * rng.uniform(0.42, 0.62)
        strikes += 1
        # typing rhythm: mostly quick, sometimes a thought
        if rng.rand() < 0.18:
            at += rng.uniform(0.09, 0.17)
        else:
            at += rng.uniform(0.024, 0.062)
    bell_t = t_all - 0.58                        # the margin bell
    bell = np.where(bell_t > 0,
                    np.sin(2 * np.pi * 1180.0 * bell_t)
                    * np.exp(-np.maximum(bell_t, 0) * 26.0), 0.0)
    return out + bell * 0.30


_RECIPES = {"click": _click, "fax": _fax}


def get_sound_path(name):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    path = os.path.join(AUDIO_DIR, "%s_v%d.wav" % (name, AUDIO_VERSION))
    if not os.path.exists(path):
        _write(path, _RECIPES[name]())
    return path
