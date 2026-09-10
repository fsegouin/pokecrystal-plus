"""Drop straight into a battle, in a window, to look at the HUD.

    .venv/bin/python tests/battle_now.py

Sets a battle up headless, which takes a few seconds, then opens a window at
the battle menu with both HUDs on screen. Play from there.

The Goldenrod saves ship with an empty party, so a mon is written into the
party first. Without one the trainer battle cannot start, and the trainer's
approach script sits waiting for a movement that never finishes.

Keys: arrow keys, A = a, B = s, START = Enter, SELECT = Backspace,
space = fast forward, Z = save state, X = load state.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import ROM, STATES, Crystal  # noqa: E402
from test_hud import reach_battle  # noqa: E402

from pyboy import PyBoy  # noqa: E402

STATE = os.path.join(STATES, "battle_now.state")


def build_state():
    """Walk into the Route 34 trainer and save a state at the battle menu."""
    with Crystal(sav=os.path.join(STATES, "fps60.sav")) as c:
        if not reach_battle(c):
            sys.exit("could not start a battle; is the trainer already beaten?")
        c.run(60)
        os.makedirs(STATES, exist_ok=True)
        with open(STATE, "wb") as f:
            c.pb.save_state(f)
        print(f"enemy L{c.read('wEnemyMonLevel')}, player L{c.read('wBattleMonLevel')}")


def play():
    pb = PyBoy(ROM, window="SDL2", cgb=True)
    with open(STATE, "rb") as f:
        pb.load_state(f)
    try:
        while pb.tick():
            pass
    finally:
        pb.stop(save=False)


if __name__ == "__main__":
    print("setting the battle up...")
    build_state()
    print("opening the window; close it when you are done")
    play()
