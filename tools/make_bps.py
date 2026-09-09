#!/usr/bin/env python3
"""Write a BPS patch turning SOURCE into TARGET.

usage: make_bps.py SOURCE.gbc TARGET.gbc OUT.bps

BPS rather than IPS: it stores CRC32s of both ROMs, so applying the patch to
the wrong file is rejected instead of silently producing a broken ROM, and it
can express a target of a different size. The patch uses only SourceRead and
TargetRead actions -- spec-valid, and copy-matching would save little on a
same-size ROM hack.
"""
import sys
import zlib

SOURCE_READ = 0
TARGET_READ = 1


def runs(src, dst):
    """Yield (offset, length, differs) spans covering the longer of the two.

    Spans are maximal, so a patch built from them has one action per span.
    """
    n = max(len(src), len(dst))
    i = 0
    while i < n:
        differs = _at(src, i) != _at(dst, i)
        j = i + 1
        while j < n and (_at(src, j) != _at(dst, j)) == differs:
            j += 1
        yield i, j - i, differs
        i = j


def _at(buf, i):
    return buf[i] if i < len(buf) else None


def varint(n):
    """BPS number encoding: 7 bits per byte, high bit marks the last one."""
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(x | 0x80)
            return bytes(out)
        out.append(x)
        n -= 1


def write_bps(src, dst, diff, path):
    body = bytearray(b"BPS1")
    body += varint(len(src)) + varint(len(dst)) + varint(0)  # no metadata
    for off, length, differs in diff:
        if off >= len(dst):
            break  # nothing past the target's end can be expressed
        length = min(length, len(dst) - off)
        body += varint(((length - 1) << 2) | (TARGET_READ if differs else SOURCE_READ))
        if differs:
            body += dst[off:off + length]
    body += zlib.crc32(src).to_bytes(4, "little")
    body += zlib.crc32(dst).to_bytes(4, "little")
    body += zlib.crc32(body).to_bytes(4, "little")
    with open(path, "wb") as f:
        f.write(body)
    return len(body)


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    with open(sys.argv[1], "rb") as f:
        src = f.read()
    with open(sys.argv[2], "rb") as f:
        dst = f.read()
    out = sys.argv[3]
    diff = list(runs(src, dst))
    changed = sum(length for _, length, differs in diff if differs)
    size = write_bps(src, dst, diff, out)
    print(f"{changed} bytes differ -> {out} ({size} B)")


if __name__ == "__main__":
    main()
