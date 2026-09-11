"""B on the battle menu puts the cursor on RUN (Crystal+).

Walks the Goldenrod save into the Route 34 trainer, then reads which option
the cursor is beside off the tilemap. B must move the cursor to RUN without
choosing anything, a second B must leave it there, the arrows must still move
it, and A on RUN must still choose it: against a trainer that prints the
"no running" message and comes back to the menu.

The Bug Contest menu takes the same path (CommonBattleMenu) and is not walked
here.

Run: .venv/bin/python tests/test_battle_menu.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import STATES, Crystal  # noqa: E402
from test_hud import reach_battle  # noqa: E402

CURSOR = 0xED  # "▶"
# The four options, as the first three tiles after the cursor. <PKMN> is one
# control code that the menu expands into two tiles, so match on PK alone.
OPTIONS = {
    "FIGHT": bytes([0x85, 0x88, 0x86]),
    "PKMN": bytes([0xE1, 0xE2]),
    "PACK": bytes([0x8F, 0x80, 0x82]),
    "RUN": bytes([0x91, 0x94, 0x8D]),
}
NO_RUNNING = bytes([0x8D, 0xAE, 0xE7])  # "No!"


class Checks:
    def __init__(self):
        self.failures = []

    def __call__(self, label, got, want):
        ok = got == want
        if not ok:
            self.failures.append(label)
        print(f"  {'ok  ' if ok else 'FAIL'} {label}: got {got!r}, want {want!r}")


def tile(c, x, y):
    return c.read("wTilemap", y * 20 + x)


def cursor_on(c):
    """The option the menu cursor is beside, or None with no menu up."""
    for y in range(12, 18):
        for x in range(8, 19):
            if tile(c, x, y) == CURSOR:
                after = bytes(tile(c, x + 1 + i, y) for i in range(3))
                for name, text in OPTIONS.items():
                    if after.startswith(text):
                        return name
    return None


def screen(c):
    return bytes(c.read("wTilemap", i) for i in range(20 * 18))


def main():
    check = Checks()
    with Crystal(sav=os.path.join(STATES, "fps60.sav")) as c:
        started = reach_battle(c)
        check("a battle started", started, True)
        if not started:
            return 1
        for _ in range(30):
            if cursor_on(c):
                break
            c.press("a", hold=8, release=8)
            c.run(30)
        check("the menu opens on FIGHT", cursor_on(c), "FIGHT")

        c.press("b", hold=8, release=8)
        c.run(20)
        check("B moves the cursor to RUN", cursor_on(c), "RUN")
        check("without leaving the battle", bool(c.read("wBattleMode")), True)

        c.press("b", hold=8, release=8)
        c.run(20)
        check("a second B leaves it there", cursor_on(c), "RUN")

        c.press("up", hold=8, release=8)
        c.run(20)
        check("the arrows still move it", cursor_on(c), "PKMN")

        c.press("b", hold=8, release=8)
        c.run(20)
        check("B from PKMN goes to RUN too", cursor_on(c), "RUN")

        c.press("a", hold=8, release=8)
        for _ in range(20):
            c.run(10)
            if NO_RUNNING in screen(c):
                break
        check("A on RUN still chooses it", NO_RUNNING in screen(c), True)
        for _ in range(10):
            c.press("a", hold=8, release=8)
            c.run(30)
            if cursor_on(c):
                break
        check("and the menu comes back on RUN", cursor_on(c), "RUN")

    print()
    if check.failures:
        print(f"{len(check.failures)} failure(s): {', '.join(check.failures)}")
        return 1
    print("all battle menu checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
