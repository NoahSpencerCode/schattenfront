#!/usr/bin/env python3
"""Repair the macOS deploy build for Apple Silicon.

Panda3D's build_apps appends the frozen module blob AFTER the Mach-O
structures of the deploy stub. Apple Silicon kills such binaries two
ways: the stale linker signature no longer matches the patched pages
(dyld: CODESIGNING Invalid Page), and even re-signed, mmap of pages
past the signature-covered region raises SIGBUS. `codesign --force`
is no cure -- it rewrites the file from its load commands and DROPS
the appended blob entirely.

The repair: thin the stub to arm64, place the blob INSIDE an extended
__LINKEDIT segment (so codesign hashes it with everything else),
patch the blobinfo headers to the blob's new offset, ad-hoc sign, and
sign every nested library. Run AFTER `python setup.py build_apps`:

    python packaging/mac_sign_fix.py [path/to/Zero Hour 1939.app]
"""
import glob
import os
import struct
import subprocess
import sys
import tempfile

BLOB_ALIGN = 16384          # arm64 page size, matches FreezeTool
LC_SEGMENT_64 = 0x19


def run(*cmd):
    subprocess.run(cmd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def fat_slices(data):
    if struct.unpack('>I', data[:4])[0] != 0xcafebabe:
        return None
    n = struct.unpack('>I', data[4:8])[0]
    out = []
    for i in range(n):
        cputype, _, off, size, _ = struct.unpack(
            '>iiIII', data[8 + 20 * i: 28 + 20 * i])
        out.append((cputype, off, size))
    return out


def extend_linkedit(macho, extra):
    """Grow __LINKEDIT's file/vm size by `extra` bytes (in place)."""
    ncmds, = struct.unpack('<I', macho[16:20])
    off = 32                                     # 64-bit mach header
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack('<II', macho[off:off + 8])
        if cmd == LC_SEGMENT_64:
            name = macho[off + 8:off + 24].rstrip(b'\0')
            if name == b'__LINKEDIT':
                vmaddr, vmsize, fileoff, filesize = struct.unpack(
                    '<QQQQ', macho[off + 24:off + 56])
                filesize += extra
                vmsize = (filesize + BLOB_ALIGN - 1) & ~(BLOB_ALIGN - 1)
                macho[off + 24:off + 56] = struct.pack(
                    '<QQQQ', vmaddr, vmsize, fileoff, filesize)
                return fileoff, filesize
        off += cmdsize
    raise SystemExit("__LINKEDIT not found")


def main():
    app = sys.argv[1] if len(sys.argv) > 1 else \
        'build/macosx_11_0_arm64/Zero Hour 1939.app'
    exe = glob.glob(os.path.join(app, 'Contents', 'MacOS', '*'))[0]
    data = open(exe, 'rb').read()
    slices = fat_slices(data)
    if slices is None:
        raise SystemExit("expected a universal stub; got thin Mach-O")
    slices_end = max(off + size for (_, off, size) in slices)
    blob_off = (slices_end + BLOB_ALIGN - 1) & ~(BLOB_ALIGN - 1)
    blob = data[blob_off:]
    if not blob:
        raise SystemExit("no appended blob -- re-run build_apps first")
    # thin to arm64 (cputype 0x0100000c)
    arm = next(s for s in slices if s[0] == 0x0100000c)
    thin = bytearray(data[arm[1]:arm[1] + arm[2]])
    print("stub: universal %d bytes -> arm64 %d; blob %d"
          % (slices_end, len(thin), len(blob)))

    # strip the stale linker signature from the CLEAN thin stub first
    # (codesign reports an internal error if asked to re-sign once the
    # segment sizes no longer match the old signature's world view)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(thin)
        tmp = tf.name
    os.chmod(tmp, 0o755)
    run('codesign', '--remove-signature', tmp)
    thin = bytearray(open(tmp, 'rb').read())
    os.unlink(tmp)
    print("unsigned thin stub: %d bytes" % len(thin))

    # blob goes at the padded end of the thin slice, inside __LINKEDIT
    new_off = (len(thin) + BLOB_ALIGN - 1) & ~(BLOB_ALIGN - 1)
    pad = new_off - len(thin)
    extend_linkedit(thin, pad + len(blob))

    # patch the blobinfo header(s) to the new offset
    needle = struct.pack('<Q', blob_off)
    patched = 0
    i = thin.find(needle)
    while i != -1:
        size_here = struct.unpack('<Q', thin[i + 8:i + 16])[0]
        if 0 < size_here <= len(blob) + 64:
            thin[i:i + 8] = struct.pack('<Q', new_off)
            patched += 1
        i = thin.find(needle, i + 8)
    if patched == 0:
        raise SystemExit("blobinfo header not found")
    print("blob %d -> %d (%d header patch(es))"
          % (blob_off, new_off, patched))

    thin += b'\0' * pad
    thin += blob

    # sign: the blob now lies inside __LINKEDIT, so its pages are
    # hashed with the rest and mmap validates cleanly
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(thin)
        tmp = tf.name
    os.chmod(tmp, 0o755)
    run('codesign', '--force', '--no-strict', '-s', '-', tmp)
    os.replace(tmp, exe)
    os.chmod(exe, 0o755)

    # the game payload must be reachable BESIDE the binary: in a
    # frozen build every module's __file__ anchors on the
    # executable's directory (Windows/Linux builds are flat, only the
    # mac bundle split ever broke this). Real files inside Contents/
    # MacOS break the code seal -- codesign demands everything there
    # be signed Mach-O -- so the payload stays in Resources and
    # SYMLINKS beside the binary carry the paths.
    res = os.path.join(app, 'Contents', 'Resources')
    macos_dir = os.path.dirname(exe)
    for d in ('assets', 'data', 'media'):
        src = os.path.join(res, d)
        link = os.path.join(macos_dir, d)
        if os.path.isdir(src) and not os.path.lexists(link):
            os.symlink(os.path.join('..', 'Resources', d), link)
            print("linked %s beside the binary" % d)

    for root, _, files in os.walk(app):
        for f in files:
            if f.endswith(('.so', '.dylib')):
                run('codesign', '--force', '-s', '-',
                    os.path.join(root, f))
    run('codesign', '--force', '--no-strict', '-s', '-', app)
    print("signed:", app)


if __name__ == '__main__':
    main()
