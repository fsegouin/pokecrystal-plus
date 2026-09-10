"""Drop straight into a battle, in a window, to look at the HUD.

    .venv/bin/python tests/battle_now.py
    .venv/bin/python tests/battle_now.py slp psn

Sets a battle up headless, which takes a few seconds, then opens a window at
the battle menu with both HUDs on screen. Play from there.

Name one or two status conditions to start with them showing, the enemy's
first: slp, psn, brn, frz or par. They take the cells the level would, so this
is how to see the widest a row ever gets.

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

# constants/pokemon_constants.asm status bits; sleep is a counter, not a bit
STATUS = {"slp": 0x05, "psn": 1 << 3, "brn": 1 << 4, "frz": 1 << 5, "par": 1 << 6}


def build_state(statuses=()):
    """Walk into the Route 34 trainer and save a state at the battle menu."""
    with Crystal(sav=os.path.join(STATES, "fps60.sav")) as c:
        if not reach_battle(c):
            sys.exit("could not start a battle; is the trainer already beaten?")
        if statuses:
            # Written straight into the battle structs. The HUD is redrawn on
            # the way through the party menu, which is the cheapest way to make
            # both sides pick the change up.
            for sym, name in zip(("wEnemyMonStatus", "wBattleMonStatus"), statuses):
                c.write(sym, STATUS[name])
            c.press("right", hold=10, release=10); c.run(20)
            c.press("a", hold=10, release=10); c.run(90)
            c.press("b", hold=10, release=10); c.run(180)
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
    names = [a.lower() for a in sys.argv[1:]]
    for n in names:
        if n not in STATUS:
            sys.exit(f"unknown status {n!r}; pick from {', '.join(STATUS)}")
    print("setting the battle up...")
    build_state(names[:2])
    print("opening the window; close it when you are done")
    play()
