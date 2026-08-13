#!/usr/bin/env python3
"""Build the shipping archives -- THE WHOLE SEQUENCE, in order.

    python make_dist.py            # both platforms
    python make_dist.py mac        # one of: mac, win

`setup.py bdist_apps` cannot be used on its own for the mac build:
it zips the app the instant build_apps finishes, and the app is not
yet fit to run. Panda's deploy stub carries the frozen program in a
blob appended AFTER the Mach-O structures, which Apple Silicon
kills on sight (CODESIGNING, Invalid Page) -- the repair in
packaging/mac_sign_fix.py has to run BETWEEN the build and the zip.
Skipping it produces an archive that looks perfect and dies before
its first instruction, which is exactly what happened once; hence
this script, so the order cannot be forgotten again.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MAC = 'macosx_11_0_arm64'
WIN = 'win_amd64'
APP = 'Global Operations 1939.app'
WIN_FOLDER = 'global-operations-1939'


def version():
    import re
    src = open(os.path.join(ROOT, 'config.py'), encoding='utf-8').read()
    m = re.search(r"^GAME_VERSION\s*=\s*'([^']+)'", src, re.M)
    return m.group(1) if m else '0.0.0'


def run(*cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, cwd=kw.get('cwd', ROOT))


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else 'both'
    py = sys.executable
    ver = version()
    dist = os.path.join(ROOT, 'dist')
    os.makedirs(dist, exist_ok=True)

    print("== 1/3  freezing the game (both platforms) ==")
    run(py, 'setup.py', 'build_apps')

    if want in ('both', 'mac'):
        app = os.path.join(ROOT, 'build', MAC, APP)
        if not os.path.isdir(app):
            raise SystemExit("no mac app at %s" % app)
        print("== 2/3  repairing the mac app (Apple Silicon) ==")
        run(py, os.path.join('packaging', 'mac_sign_fix.py'), app)
        # the seal must hold or the archive is worthless
        run('codesign', '--verify', '--deep', '--strict', app)
        out = os.path.join(dist,
                           'global-operations-1939-%s_%s.zip' % (ver, MAC))
        if os.path.exists(out):
            os.remove(out)
        print("== 3/3  archiving the mac app ==")
        # ditto, not zip: it keeps the symlinks beside the binary and
        # the signature intact
        run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
            APP, out, cwd=os.path.join(ROOT, 'build', MAC))
        print("   ->", out)

    if want in ('both', 'win'):
        src = os.path.join(ROOT, 'build', WIN)
        if not os.path.isdir(src):
            raise SystemExit("no windows build at %s" % src)
        out = os.path.join(dist,
                           'global-operations-1939-%s_%s.zip' % (ver, WIN))
        if os.path.exists(out):
            os.remove(out)
        print("== archiving the windows build ==")
        # the archive opens on ONE folder, as the deploy tool's own
        # zip did: global-operations-1939/...
        staged = os.path.join(ROOT, 'build', '_win_stage', WIN_FOLDER)
        if os.path.isdir(os.path.dirname(staged)):
            shutil.rmtree(os.path.dirname(staged))
        shutil.copytree(src, staged, symlinks=True)
        shutil.make_archive(out[:-4], 'zip',
                            os.path.dirname(staged))
        shutil.rmtree(os.path.dirname(staged))
        print("   ->", out)

    print()
    print("archives in dist/:")
    for f in sorted(os.listdir(dist)):
        p = os.path.join(dist, f)
        print("   %-58s %6.0f MB" % (f, os.path.getsize(p) / 1e6))


if __name__ == '__main__':
    main()
