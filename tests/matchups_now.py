"""Drop into a wild battle whose move list shows all three matchup markers.

    .venv/bin/python tests/matchups_now.py           # set up, then play in a window
    .venv/bin/python tests/matchups_now.py --check   # headless: open FIGHT, report, screenshot

Sets the battle up headless, which takes a few seconds, then opens a window at
the battle menu. Pick FIGHT. The lead knows four moves and the foe is a
Normal/Flying type from the Route 34 grass, so the list reads:

    LICK          ×   Normal takes nothing from Ghost
    THUNDERSHOCK  ▲   Electric is super effective on Flying
    VINE WHIP     ▼   Flying resists Grass
    TACKLE            even, so no marker

A pure Normal type cannot show all three: it resists nothing. The lead's
moves are written straight into the party, and the wild randomizer is switched
off for this session only, so the grass rolls from its own table. Pidgey (by
day) and Hoothoot (at night) are the Normal/Flying slots. When it rolls
anything else, a hook swaps the species for a Pidgey at the moment the battle
copies it, in LoadTrainerOrWildMonPic.
Needs tests/states/chain0.sav, which make_chain_save.py writes.

Keys: arrow keys, A = a, B = s, START = Enter, SELECT = Backspace,
space = fast forward, Z = save state, X = load state.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import ROM, STATES, Crystal  # noqa: E402
from test_fixes import constants  # noqa: E402

from pyboy import PyBoy  # noqa: E402

SAVE = os.path.join(STATES, "chain0.sav")
STATE = os.path.join(STATES, "matchups_now.state")

MOVES = constants("move_constants")
SPECIES = constants("pokemon_constants")
LEAD_MOVES = ["LICK", "THUNDERSHOCK", "VINE_WHIP", "TACKLE"]
EXPECTED = "×▲▼ "
# the Normal/Flying types in the Route 34 grass
FOES = {SPECIES[n]: n for n in ("PIDGEY", "HOOTHOOT")}
PLUS_WILD_ENABLED = 1 << 0

FIGHT = bytes([0x85, 0x88, 0x86, 0x87, 0x93])  # "FIGHT" in the charmap
L_OF_LICK = 0x8B
MARK = {0xBD: "▲", 0xEE: "▼", 0xF1: "×", 0x7F: " "}


def screen(c):
    return bytes(c.read("wTilemap", i) for i in range(20 * 18))


def build_state():
    """Walk the grass into a Normal/Flying foe and save a state at the battle menu."""
    if not os.path.exists(SAVE):
        sys.exit(f"missing {SAVE}: run tests/make_chain_save.py first")
    with Crystal(sav=SAVE) as c:
        c.continue_game()
        for i, name in enumerate(LEAD_MOVES):
            c.write("wPartyMon1Moves", MOVES[name], i)
            c.write("wPartyMon1PP", 20, i)
        c.write("wPlusFlags", c.read("wPlusFlags") & ~PLUS_WILD_ENABLED)
        c.write("wRepelEffect", 0)
        c.write("wTempWildMonSpecies", 0)

        # LoadTrainerOrWildMonPic is where the battle copies the rolled species
        # for itself, so swapping it on the way in is the one moment that can
        # neither be too early (the roll is done) nor too late.
        def swap_foe(_):
            if c.read("wTempWildMonSpecies") not in FOES:
                c.write("wTempWildMonSpecies", SPECIES["PIDGEY"])
        c.pb.hook_register(*c.syms["LoadTrainerOrWildMonPic"], swap_foe, None)

        # chain0.sav stands in the grass with grass on the tile to the west,
        # so pacing between the two keeps every step in it.
        for i in range(400):
            c.press("left" if i % 2 == 0 else "right", hold=16, release=24)
            if c.read("wTempWildMonSpecies"):
                break
        else:
            sys.exit("no wild encounter in 400 steps")

        for _ in range(60):
            if FIGHT in screen(c):
                break
            c.press("a", hold=8, release=8)
            c.run(20)
        c.run(30)
        foe = c.read("wEnemyMonSpecies")
        if foe not in FOES:
            sys.exit(f"the battle loaded species {foe}, not a Normal/Flying type")
        with open(STATE, "wb") as f:
            c.pb.save_state(f)
        return FOES[foe], c.read("wEnemyMonLevel")


def check():
    """Open FIGHT headless from the saved state and report the markers."""
    with Crystal() as c:
        with open(STATE, "rb") as f:
            c.pb.load_state(f)
        for _ in range(20):
            c.press("a", hold=8, release=8)
            c.run(30)
            if c.read("wTilemap", 13 * 20 + 6) == L_OF_LICK:
                break
        c.run(20)
        got = "".join(MARK.get(c.read("wTilemap", (13 + r) * 20 + 18), "?") for r in range(4))
        shot = os.path.join(tempfile.gettempdir(), "plus_matchups_now.png")
        c.pb.screen.image.resize((640, 576)).save(shot)
        return got, shot


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
    foe, level = build_state()
    print(f"a wild {foe} L{level}; the moves should read {EXPECTED!r} down the list")
    if "--check" in sys.argv[1:]:
        got, shot = check()
        print(f"markers {got!r} ({'as expected' if got == EXPECTED else 'NOT as expected'})")
        print(f"screenshot: {shot}")
        sys.exit(0 if got == EXPECTED else 1)
    print("opening the window: pick FIGHT, then close it when you are done")
    play()
