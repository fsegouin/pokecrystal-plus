"""Build save files for trying the shiny chain by hand.

    .venv/bin/python tests/make_chain_save.py

Writes two battery saves into tests/states/:

  chain0.sav   standing in the Route 34 grass with a healthy party, no chain
  chain39.sav  the same spot, one win away from the top tier

Battery saves are ROM independent, so these survive a rebuild.

The player starts in Goldenrod, so this walks south to Route 34, fights the
trainer who blocks the way, and steps into the grass. The position is captured
by calling SaveGameData, which writes the save block to SRAM; the chain is
written separately by PlusChainStore, since it lives outside the save block.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import ROOT, STATES, Crystal  # noqa: E402
from test_hud import give_party_mon  # noqa: E402

GRASS_STEPS = 3  # west off the path at the point the trainer stops blocking
QUILAVA, LEVEL = 156, 40
FLAME_WHEEL = 172  # wanted in the first slot: chaining means a lot of battles,
                   # and the level-40 move list opens on Smokescreen


def free_the_player(c, limit=400):
    """Mash A until nothing owns the loop: text, or the trainer on the way."""
    for _ in range(limit):
        if c.read("wBattleMode") == 0 and not c.read("wScriptRunning"):
            return True
        c.press("a", hold=8, release=6)
    return False


def build(name, chain_species, chain_count):
    with Crystal(sav=os.path.join(STATES, "fps60.sav")) as c:
        c.continue_game()
        give_party_mon(c, level=40, hp=140)
        for _ in range(14):
            c.press("down", hold=16, release=10)
        if not free_the_player(c):
            sys.exit("could not get walking control back on Route 34")
        for _ in range(GRASS_STEPS):
            c.press("left", hold=16, release=10)
        where = (c.read("wMapGroup"), c.read("wMapNumber"))
        xy = (c.read("wXCoord"), c.read("wYCoord"))

        # The mon that walked here was written straight into memory, which is
        # fine for getting past the trainer but does not survive a save: the
        # game recomputes its stats on load and it comes back unusable. Build
        # a real one through the game's own code now that walking is done.
        c.write("wPartyCount", 0)
        c.write("wMonType", 0)  # PARTYMON
        c.write("wCurPartySpecies", QUILAVA)
        c.write("wCurPartyLevel", LEVEL)
        c.call("TryAddMonToParty", frames=30)
        if c.read("wPartyCount") != 1:
            sys.exit("could not generate the party mon")
        # Put the damaging move first so a chain can be ground out on the A
        # button. Whatever sits in slot one is swapped with Flame Wheel.
        moves = [c.read("wPartyMon1Moves", i) for i in range(4)]
        pp = [c.read("wPartyMon1PP", i) for i in range(4)]
        if FLAME_WHEEL in moves and moves[0] != FLAME_WHEEL:
            j = moves.index(FLAME_WHEEL)
            moves[0], moves[j] = moves[j], moves[0]
            pp[0], pp[j] = pp[j], pp[0]
            for i in range(4):
                c.write("wPartyMon1Moves", moves[i], i)
                c.write("wPartyMon1PP", pp[i], i)

        hp = (c.read("wPartyMon1MaxHP"), c.read("wPartyMon1MaxHP", 1))
        c.write("wPartyMon1HP", hp[0])
        c.write("wPartyMon1HP", hp[1], 1)

        c.call("PlusChainWriteOff", a=0)  # the base save may have it switched off
        c.call("PlusChainStore", d=chain_species, e=chain_count)
        c.call("SaveGameData", frames=60)
        c.pb.stop(save=True)

    written = os.path.join(ROOT, "pokecrystal.gbc.ram")
    if not os.path.exists(written):
        sys.exit("PyBoy did not write the battery save")
    out = os.path.join(STATES, name)
    shutil.move(written, out)
    print(f"{name}: map {where} at {xy}, chain {chain_species}/{chain_count}, "
          f"Quilava L{LEVEL} on {hp[0] * 256 + hp[1]} HP, moves {moves}")
    return out


if __name__ == "__main__":
    os.makedirs(STATES, exist_ok=True)
    build("chain0.sav", 0, 0)
    build("chain39.sav", RATTATA := 19, 39)
    print("\nplay one with:  .venv/bin/python tests/playtest.py chain39")
