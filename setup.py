"""Release packaging: `python setup.py bdist_apps` builds the game
for macOS and Windows from any host (Panda3D deploy tools assemble
per-platform wheels; nothing is compiled locally).

The detail-tile cache (4 GB, rebuilt lazily in play) and the
preprocessing sources stay out of the bundle; everything the game
READS at runtime ships prebuilt so first launch pays no bake.
"""
import os
import re

from setuptools import setup


def _const(module, name):
    """One module-level integer constant, read WITHOUT importing the
    module (geodata pulls numpy and the whole map machine)."""
    src = open(module, 'r', encoding='utf-8').read()
    # the constant may be declared alone or in a tuple assignment
    # (MASK_W, MASK_H = 8192, 4096)
    m = re.search(r'^%s\s*=\s*(\d+)' % name, src, re.M)
    if not m:
        m = re.search(r'^%s\s*,\s*\w+\s*=\s*(\d+)' % name, src,
                      re.M)
    if not m:
        raise SystemExit("setup.py cannot read %s from %s"
                         % (name, module))
    return int(m.group(1))


# THE BAKED CACHES SHIP BY THE VERSIONS THE CODE ASKS FOR, never by
# a list typed out by hand: a bumped constant used to leave the
# bundle carrying last version's file, and the shipped game then
# tried to BAKE the map on the player's machine at first launch.
_CACHE_V = _const('geodata.py', 'CACHE_VERSION')
_TEX_V = _const('geodata.py', 'TEXTURE_VERSION')
_MASK_W = _const('geodata.py', 'MASK_W')
_FINE_W = _const('geodata.py', 'FINE_W')
_CACHES = [
    'data/cache/vectors_v%d.npz' % _CACHE_V,
    'data/cache/globe_map_v%d.png' % _TEX_V,
    'data/cache/land_mask_v%d_%d.npy' % (_CACHE_V, _MASK_W),
    'data/cache/land_bits_v%d_%d.npy' % (_CACHE_V, _FINE_W),
    'data/cache/coast_dist_v1_2048.npy',
    # the two DERIVED relief grids, 18 MB apiece. The 466 MB
    # etopo1_60s source they were milled from is NOT shipped:
    # terrain.ensure_dem returns these two the moment it finds
    # them, and never looks at the source again.
    'data/cache/etopo1_5m_i2.npy',
    'data/cache/etopo1_5ms_i2.npy',
    'data/cache/land_stitch_v2_*.npz',
]
for _p in _CACHES:
    if '*' not in _p and not os.path.exists(_p):
        raise SystemExit(
            "setup.py: %s is not baked -- run the game once to bake "
            "it before building the dist" % _p)

_VERSION = _const('config.py', 'GAME_VERSION') if False else None
_m = re.search(r"^GAME_VERSION\s*=\s*'([^']+)'",
               open('config.py', 'r', encoding='utf-8').read(), re.M)
_VERSION = _m.group(1) if _m else '0.0.0'

setup(
    name='global-operations-1939',
    version=_VERSION,
    options={
        'build_apps': {
            'gui_apps': {'Global Operations 1939': 'main.py'},
            'icons': {'Global Operations 1939': [
                'packaging/icon-1024.png', 'packaging/icon-512.png',
                'packaging/icon-256.png', 'packaging/icon-128.png',
                'packaging/icon-64.png', 'packaging/icon-48.png',
                'packaging/icon-32.png', 'packaging/icon-16.png']},
            'log_filename': '$USER_APPDATA/Global Operations 1939/output.log',
            'log_append': False,
            'plugins': ['pandagl', 'p3openal_audio', 'p3ffmpeg'],
            # numpy's add_newdoc pulls this test extension at import
            # time in builds that keep docstrings; the freezer misses
            # it and the shipped game dies on launch without it
            'include_modules': {'*': ['numpy.core._multiarray_tests']},
            'platforms': ['macosx_11_0_arm64', 'win_amd64'],
            'requirements_path': 'requirements.txt',
            'include_patterns': [
                'assets/**',
                'media/reel.mp4',
                # THE SCORE: the pack's marches (ogg only -- the wav
                # and mp3 copies would treble the bundle), the one
                # looping march the menu stands on, and the recorded
                # addresses
                'media/WW2 Military Music Pack/Tracks/ogg/*.ogg',
                'media/WW2 Military Music Pack/Loops/ogg/*.ogg',
                'media/speeches/*.mp3',
                'data/*.geojson',
            ] + _CACHES,
            'exclude_patterns': [
                'venv/**', 'packaging/**', 'build/**', 'dist/**',
                'data/cache/tiles_*/**', '**/*.pyc',
                # dev leavings that would ride along in the bundle
                'assets/icons/_gen/**', '**/.DS_Store',
                'saves/**', 'tests/**', 'docs/**',
            ],
        },
        'bdist_apps': {
            'installers': {
                'macosx_11_0_arm64': 'zip',
                'win_amd64': 'zip',
            },
        },
    },
)
