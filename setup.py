"""Release packaging: `python setup.py bdist_apps` builds the game
for macOS and Windows from any host (Panda3D deploy tools assemble
per-platform wheels; nothing is compiled locally).

The detail-tile cache (4 GB, rebuilt lazily in play) and the
preprocessing sources stay out of the bundle; everything the game
READS at runtime ships prebuilt so first launch pays no bake.
"""
from setuptools import setup

setup(
    name='schattenfront',
    version='0.1.1',
    options={
        'build_apps': {
            'gui_apps': {'Schattenfront': 'main.py'},
            'icons': {'Schattenfront': [
                'packaging/icon-1024.png', 'packaging/icon-512.png',
                'packaging/icon-256.png', 'packaging/icon-128.png',
                'packaging/icon-64.png', 'packaging/icon-48.png',
                'packaging/icon-32.png', 'packaging/icon-16.png']},
            'log_filename': '$USER_APPDATA/Schattenfront/output.log',
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
                'data/*.geojson',
                'data/cache/vectors_v5.npz',
                'data/cache/globe_map_v36.png',
                'data/cache/land_mask_v5.npy',
                'data/cache/land_mask_v5_8192.npy',
                'data/cache/land_bits_v5_32768.npy',
                'data/cache/coast_dist_v1_2048.npy',
                'data/cache/etopo1_60s_i2.npy',
                'data/cache/etopo1_5m_i2.npy',
                'data/cache/etopo1_5ms_i2.npy',
                'data/cache/land_stitch_v2_*.npz',
            ],
            'exclude_patterns': [
                'venv/**', 'packaging/**', 'build/**', 'dist/**',
                'data/cache/tiles_*/**', '**/*.pyc',
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
