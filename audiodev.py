"""
THE AUDIO WATCH -- which loudspeaker does the system point at?

OpenAL opens the default output device ONCE, at launch, and never
follows it afterwards: headphones plugged in mid-session moved the
system's sound over while the game kept talking to the old device
-- dead silence. The cure is to notice the move and rebuild the
audio managers on the new device (game.restart_audio).

This module answers one question -- the CoreAudio id of the current
default output -- via ctypes, so no extra dependency is shipped.
On any other platform, or any error, it answers None and the watch
simply never engages.
"""

import ctypes
import ctypes.util
import struct
import sys

_core_audio = None


def _fourcc(s):
    return struct.unpack('>I', s.encode('ascii'))[0]


class _PropertyAddress(ctypes.Structure):
    _fields_ = [('selector', ctypes.c_uint32),
                ('scope', ctypes.c_uint32),
                ('element', ctypes.c_uint32)]


# kAudioObjectSystemObject; kAudioHardwarePropertyDefaultOutputDevice
# in kAudioObjectPropertyScopeGlobal
_SYSTEM_OBJECT = 1
_ADDR = None


def default_output_device():
    """The CoreAudio id of the system's default output device, or
    None when it cannot be read (not macOS, no device, any error)."""
    global _core_audio, _ADDR
    if sys.platform != 'darwin':
        return None
    try:
        if _core_audio is None:
            path = ctypes.util.find_library('CoreAudio')
            if not path:
                return None
            _core_audio = ctypes.CDLL(path)
            _ADDR = _PropertyAddress(_fourcc('dOut'), _fourcc('glob'),
                                     0)
        dev = ctypes.c_uint32(0)
        size = ctypes.c_uint32(4)
        err = _core_audio.AudioObjectGetPropertyData(
            _SYSTEM_OBJECT, ctypes.byref(_ADDR), 0, None,
            ctypes.byref(size), ctypes.byref(dev))
        if err != 0 or dev.value == 0:
            return None
        return int(dev.value)
    except Exception:
        return None
