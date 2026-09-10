"""Play the ROM in a window and keep the save.

    .venv/bin/python tests/playtest.py gamecorner

Opens pokecrystal.gbc, loading tests/states/<name>.sav if it already exists so
you can carry on from where you left off. Play to wherever you want checked,
save in game (START, SAVE, YES), then close the window. The battery save is
written to tests/states/<name>.sav.

Battery saves are ROM independent, so one survives a rebuild. A PyBoy save
state (Z in the window) does not: it embeds CPU state and only loads into the
exact build it came from. Prefer this for handing a position over.

Keys: arrow keys, A = a, B = s, START = Enter, SELECT = Backspace,
space = fast forward, Z = save state, X = load state.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import ROM, STATES  # noqa: E402

from pyboy import PyBoy  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    name = sys.argv[1]
    os.makedirs(STATES, exist_ok=True)
    sav = os.path.join(STATES, name + ".sav")

    ram = None
    if os.path.exists(sav):
        ram = open(sav, "rb")
        print(f"resuming from {sav}")
    else:
        print(f"new game; will save to {sav}")

    pb = PyBoy(ROM, window="SDL2", cgb=True, ram_file=ram)
    try:
        while pb.tick():
            pass
    finally:
        # stop(save=True) writes the battery file next to the ROM
        pb.stop(save=True)
        if ram:
            ram.close()
        dumped = ROM + ".ram"
        if os.path.exists(dumped):
            shutil.move(dumped, sav)
            print(f"saved {sav} ({os.path.getsize(sav)} bytes)")
        else:
            print("no battery save was written; did you save in game?")


if __name__ == "__main__":
    main()
