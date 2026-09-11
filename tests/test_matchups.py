"""Type matchup markers on the battle move list (Crystal+).

Each of the player's moves gets a marker in the cell after its name: the up
arrow when the chart makes it super effective against the enemy's current
types, the down arrow when it is resisted, and a cross when it has no effect.
Status moves, Counter and Mirror Coat get none, and the fixed-damage moves
only ever show the cross, since an immunity is the one part of the chart they
obey.

The placement routine is called on its own from a cold boot for the chart
cases. A real battle then opens the FIGHT menu, to prove the hook and the
borrowed arrow tile are wired up.

Run: .venv/bin/python tests/test_matchups.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import STATES, Crystal  # noqa: E402
from test_fixes import constants  # noqa: E402
from test_hud import reach_battle  # noqa: E402

TYPES = constants("type_constants")
MOVES = constants("move_constants")
BATTLE = constants("battle_constants")
UNUSED_TYPES = TYPES["STEEL"] + 1
UNUSED_TYPES_END = TYPES["CURSE_TYPE"] + 1

UP, DOWN, CROSS, BLANK = 0xBD, 0xEE, 0xF1, 0x7F  # PLUS_MATCHUP_ARROW_TILE, "▼", "×", " "
MARK = {UP: "▲", DOWN: "▼", CROSS: "×", BLANK: " "}
COLUMN, FIRST_ROW, WIDTH = 18, 13, 20
T_OF_TACKLE = 0x93


class Checks:
    def __init__(self):
        self.failures = []

    def __call__(self, label, got, want):
        ok = got == want
        if not ok:
            self.failures.append(label)
        print(f"  {'ok  ' if ok else 'FAIL'} {label}: got {got!r}, want {want!r}")


def hidden_power_type(atk, dfn):
    """HiddenPowerDamage's type, from the Attack and Defense DVs."""
    t = ((atk & 3) << 2 | (dfn & 3)) + 1
    if t >= TYPES["BIRD"]:
        t += 1
    if t >= UNUSED_TYPES:
        t += UNUSED_TYPES_END - UNUSED_TYPES
    return t


def dvs_for(type_name):
    for atk in range(16):
        for dfn in range(16):
            if hidden_power_type(atk, dfn) == TYPES[type_name]:
                return atk << 4 | dfn
    raise ValueError(type_name)


def cell(row):
    return (FIRST_ROW + row) * WIDTH + COLUMN


def place(c, moves, types, identified=False, dvs=0, fill=BLANK):
    for i in range(4):
        c.write("wBattleMonMoves", MOVES[moves[i]] if i < len(moves) else 0, i)
    c.write("wEnemyMonType1", TYPES[types[0]])
    c.write("wEnemyMonType2", TYPES[types[-1]])
    c.write("wEnemySubStatus1", 1 << BATTLE["SUBSTATUS_IDENTIFIED"] if identified else 0)
    c.write("wBattleMonDVs", dvs)
    for r in range(4):
        c.write("wTilemap", fill, offset=cell(r))
    c.write("hBattleTurn", 1)
    c.write("wPlayerMoveStructType", 0x55)
    c.call("PlusPlaceMatchupMarkers", frames=8)
    return "".join(MARK.get(c.read("wTilemap", cell(r)), "?") for r in range(4))


def check_chart(c, check):
    print("the chart")
    cases = [
        ("fire and water into grass/poison", ["FLAMETHROWER", "WATER_GUN", "TACKLE", "GROWL"],
         ["GRASS", "POISON"], "▲▼  "),
        ("4x counts as super effective", ["ICE_BEAM"], ["GRASS", "FLYING"], "▲   "),
        ("2x and 1/2x cancel out", ["FLAMETHROWER"], ["WATER", "GRASS"], "    "),
        ("into a ghost", ["TACKLE", "SEISMIC_TOSS", "NIGHT_SHADE", "SHADOW_BALL"], ["GHOST"], "×× ▲"),
        ("fixed damage into a normal type", ["NIGHT_SHADE", "SEISMIC_TOSS", "SONICBOOM", "SUPER_FANG"],
         ["NORMAL"], "×   "),
        ("Counter, Mirror Coat, Earthquake, Thunderbolt into flying",
         ["COUNTER", "MIRROR_COAT", "EARTHQUAKE", "THUNDERBOLT"], ["FLYING"], "  ×▲"),
        ("status moves", ["CURSE", "GROWL", "THUNDER_WAVE"], ["GHOST"], "    "),
    ]
    for label, moves, types, want in cases:
        check(label, place(c, moves, types), want)
    check("Foresight lifts the ghost's immunity", place(c, ["TACKLE", "NIGHT_SHADE"], ["GHOST"], identified=True),
          "    ")
    check("Hidden Power as fire into grass", place(c, ["HIDDEN_POWER"], ["GRASS"], dvs=dvs_for("FIRE")), "▲   ")
    check("Hidden Power as water into grass", place(c, ["HIDDEN_POWER"], ["GRASS"], dvs=dvs_for("WATER")), "▼   ")
    check("borrowed battle variables put back", (c.read("hBattleTurn"), c.read("wPlayerMoveStructType")),
          (1, 0x55))
    place(c, ["TACKLE"], ["GHOST"], fill=0x12)
    check("rows with no move are left alone",
          [c.read("wTilemap", cell(r)) for r in range(4)], [CROSS, 0x12, 0x12, 0x12])


def check_in_battle(c, check):
    print("in a battle")
    started = reach_battle(c)
    check("a battle started", started, True)
    if not started:
        return

    def open_fight(types):
        c.write("wEnemyMonType1", TYPES[types[0]])
        c.write("wEnemyMonType2", TYPES[types[-1]])
        c.write("wTilemap", 0, offset=FIRST_ROW * WIDTH + 6)
        for _ in range(20):
            if c.read("wTilemap", FIRST_ROW * WIDTH + 6) == T_OF_TACKLE:
                c.run(10)
                return "".join(MARK.get(c.read("wTilemap", cell(r)), "?") for r in range(2))
            c.press("a", hold=8, release=8)
            c.run(30)
        return None

    # the party mon knows TACKLE and EMBER
    check("TACKLE and EMBER against a grass type", open_fight(["GRASS"]), " ▲")
    bank, addr = c.syms["FontsExtra2_UpArrowGFX"]
    want = bytes(c.pb.memory[bank, addr + i] for i in range(16))
    got = bytes(c.pb.memory[0, 0x8800 + (UP - 0x80) * 16 + i] for i in range(16))
    check("the up arrow is in its borrowed slot", got, want)
    shot = os.path.join(tempfile.gettempdir(), "plus_matchups.png")
    c.screenshot(shot)
    print(f"  screenshot: {shot}")

    c.press("b", hold=8, release=8)
    c.run(60)
    check("and against a ghost, after going back", open_fight(["GHOST"]), "× ")


def main():
    check = Checks()
    with Crystal() as c:
        c.run(600)  # boot far enough that the stack and ROM bank are live
        check_chart(c, check)
    with Crystal(sav=os.path.join(STATES, "fps60.sav")) as c:
        check_in_battle(c, check)

    print()
    if check.failures:
        print(f"{len(check.failures)} failure(s): {', '.join(check.failures)}")
        return 1
    print("all matchup checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
