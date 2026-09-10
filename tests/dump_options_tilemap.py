"""Dump the options screen's background tilemap to a file.

Used to prove the first page of the options menu is unchanged: run it against
a build without the SELECT sub-page, then against one with it, and diff.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nav  # noqa: E402
from boot import overworld  # noqa: E402


def open_options(c):
    nav.to_new_bark_town(c)
    c.run(60)
    c.press("start")
    c.run(50)
    for _ in range(4):
        c.press("down")
        c.run(20)
    c.press("a")
    c.run(80)


def dump(c):
    tm = c.pb.tilemap_background
    return [list(tm[0:20, y]) for y in range(18)]


if __name__ == "__main__":
    out = sys.argv[1]
    with overworld() as c:
        open_options(c)
        rows = dump(c)
        with open(out, "w") as f:
            for r in rows:
                f.write(" ".join(f"{t:02x}" for t in r) + "\n")
        c.screenshot(out + ".png")
    print("wrote", out)
