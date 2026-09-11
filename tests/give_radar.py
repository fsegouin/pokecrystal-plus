"""Put the POKe RADAR into a save that already exists, keeping its progress.

    .venv/bin/python tests/give_radar.py chain39

Loads tests/states/<name>.sav, adds the radar to the key items pocket if it is
not already there, and saves in place. The key items pocket is inside the
checksummed save block, so this goes through the game's own SaveGameData
rather than patching bytes in the file.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import ROOT, STATES, Crystal  # noqa: E402

POKE_RADAR = 0x2D
MAX_KEY_ITEMS = 25  # constants/item_data_constants.asm


def give(name):
    path = os.path.join(STATES, name + ".sav")
    if not os.path.exists(path):
        sys.exit(f"no such save: {path}")
    with Crystal(sav=path) as c:
        c.continue_game()
        n = c.read("wNumKeyItems")
        held = [c.read("wKeyItems", i) for i in range(n)]
        if POKE_RADAR in held:
            print(f"{name}: already has the radar ({held})")
            return
        # The pocket is a flat list of item ids, terminated with -1. There are
        # no quantities here, unlike the items pocket.
        if n >= MAX_KEY_ITEMS:
            sys.exit(f"{name}: the key items pocket is full ({n})")
        c.write("wKeyItems", POKE_RADAR, n)
        c.write("wKeyItems", 0xFF, n + 1)
        c.write("wNumKeyItems", n + 1)
        c.call("SaveGameData", frames=60)
        chain = (c.read("sPlusChainSpecies"), c.read("sPlusChainCount"))
        c.pb.stop(save=True)

    written = os.path.join(ROOT, "pokecrystal.gbc.ram")
    if not os.path.exists(written):
        sys.exit("PyBoy did not write the battery save")
    shutil.move(written, path)
    print(f"{name}: radar added, key items now {n + 1}, chain {chain[0]}/{chain[1]}")


if __name__ == "__main__":
    for arg in sys.argv[1:] or ["chain39"]:
        give(arg)
