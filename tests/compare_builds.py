"""Run the same input on two builds and check they stay in lockstep.

With the 60 fps option off, every branch added for it takes the vanilla path,
so the game should behave exactly as it did before. This drives both ROMs from
power-on with an identical button script and compares the screen and the
overworld state at every checkpoint.

    .venv/bin/python tests/compare_builds.py <other.gbc>
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nav  # noqa: E402
from boot import new_game  # noqa: E402
from harness import Crystal  # noqa: E402

WATCH = ["wMapGroup", "wMapNumber", "wYCoord", "wXCoord", "hSCX", "hSCY",
         "wOptions", "wOptions2", "wPlayerStepFlags"]


def screen_hash(c):
    return hashlib.sha1(c.pb.screen.ndarray.tobytes()).hexdigest()[:12]


def state(c):
    return tuple(c.read(s) for s in WATCH) + (screen_hash(c),)


def script(c):
    """A fixed sequence, sampled at every step."""
    out = []
    new_game(c)
    out.append(("new game", state(c)))
    nav.to_new_bark_town(c)
    out.append(("outside", state(c)))
    for button in ("right", "right", "down", "left", "up", "up", "left"):
        nav.step(c, button)
        out.append((button, state(c)))
    for hold, frames in (("right", 90), ("down", 90)):
        c.pb.button_press(hold)
        c.run(frames)
        c.pb.button_release(hold)
        c.run(30)
        out.append((f"hold {hold}", state(c)))
    c.run(600)
    out.append(("idle", state(c)))
    return out


if __name__ == "__main__":
    other = sys.argv[1]
    with Crystal() as a:
        left = script(a)
    with Crystal(rom=other) as b:
        right = script(b)

    bad = 0
    for (n1, s1), (n2, s2) in zip(left, right):
        same = s1 == s2
        if not same:
            bad += 1
            diffs = [f"{k}: {x} vs {y}"
                     for k, x, y in zip(WATCH + ["screen"], s1, s2) if x != y]
            print(f"  [DIFF] after {n1}: " + ", ".join(diffs))
        else:
            print(f"  [same] after {n1}")
    print("\nidentical" if not bad else f"\n{bad} checkpoints differ")
    sys.exit(1 if bad else 0)
