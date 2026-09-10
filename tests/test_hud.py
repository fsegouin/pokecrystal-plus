"""Checks for the one-line battle HUD.

Vanilla puts a nickname on one row and the gender symbol and level on the
next, because a ten character name fills the eleven tile row on its own.
Drawing only the NAME in a five pixel font leaves room for both beside it, so
the name comes down onto the bar's own row. The gender symbol, the ":L" and
the digits keep the game's own graphics, copied into the narrow font at build
time by tools/make_half_font.py.

The checks are:
  * the name fits the tiles the composer claims it filled, for short names,
    long names and lowercase;
  * the longest name, ten characters, still leaves room for a gender symbol
    and a three digit level in the eleven tiles the row has;
  * a character with no glyph is skipped rather than drawing rubbish;
  * both HUDs point at their own composed tiles once a battle is running;
  * the whole row is set against the HP bar's right hand end, so the level
    lands in the same column whatever the name's length, and a short name
    pushes the row right rather than leaving a gap;
  * a status condition is drawn in the level's place, and the five
    conditions are all distinct.

The layout checks call the composer on its own from a cold boot, which needs
no save. The in-battle checks walk the Goldenrod save into the Route 34
trainer; that save has an empty party, so a mon is written into it first,
otherwise the battle cannot start and the trainer's approach script waits for
a movement that never comes.

Run: .venv/bin/python tests/test_hud.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import STATES, Crystal  # noqa: E402

# constants/plus_constants.asm
PLUS_HUD_TILES = 11         # tiles the row is given
PLUS_HUD_ALIGN_TILES = 10   # the level is set against the HP bar's right end
PLUS_HUD_GLYPH_W = 5        # the condensed name's advance
# not an asm constant: the copied glyphs keep their original width
PLUS_HUD_WIDE_W = 8
# neither HUD has eleven blank font slots in a row, so each takes two
ENEMY_TILES = list(range(0xC6, 0xD0)) + [0xE4]
PLAYER_TILES = list(range(0xD7, 0xDF)) + [0xBA, 0xBB, 0xBC]

TILE_1BPP_SIZE = 8
ROW_BYTES = PLUS_HUD_TILES * TILE_1BPP_SIZE

QUILAVA = 156

# constants/charmap.asm
CHAR = {**{chr(c): 0x80 + c - ord("A") for c in range(ord("A"), ord("Z") + 1)},
        **{chr(c): 0xA0 + c - ord("a") for c in range(ord("a"), ord("z") + 1)},
        **{chr(c): 0xF6 + c - ord("0") for c in range(ord("0"), ord("9") + 1)},
        " ": 0x7F, "@": 0x50, ".": 0xE8, ":": 0x9C, "-": 0xE3, "'": 0xE0}

failures = []


def check(ok, what, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}" + (f"   ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(f"{what}: {detail}")


def encode(s):
    return [CHAR[ch] for ch in s] + [CHAR["@"]]


def give_party_mon(c, species=QUILAVA, level=40, hp=120):
    """Write a healthy party mon straight into memory.

    The battle saves ship with an empty party, and a trainer battle that
    cannot start leaves the approach script waiting on a movement forever.
    """
    c.write("wPartyCount", 1)
    c.write("wPartySpecies", species)
    c.write("wPartySpecies", 0xFF, 1)
    c.write("wPartyMon1Species", species)
    c.write("wPartyMon1Item", 0)
    for i, move in enumerate((33, 52, 0, 0)):      # TACKLE, EMBER
        c.write("wPartyMon1Moves", move, i)
    for i, pp in enumerate((35, 25, 0, 0)):
        c.write("wPartyMon1PP", pp, i)
    c.write("wPartyMon1DVs", 0xFF)
    c.write("wPartyMon1DVs", 0xFF, 1)
    c.write("wPartyMon1Happiness", 70)
    c.write("wPartyMon1Level", level)
    c.write("wPartyMon1Status", 0)
    for sym in ("wPartyMon1HP", "wPartyMon1MaxHP"):
        c.write(sym, hp >> 8)
        c.write(sym, hp & 0xFF, 1)
    for i, stat in enumerate((80, 70, 85, 90, 75)):   # Atk, Def, Spd, SAtk, SDef
        c.write("wPartyMon1MaxHP", stat >> 8, 2 + i * 2)
        c.write("wPartyMon1MaxHP", stat & 0xFF, 3 + i * 2)
    for i, b in enumerate(encode("QUILAVA") + [CHAR["@"]] * 3):
        c.write("wPartyMonNicknames", b, i)
    for i, b in enumerate(encode("RED") + [CHAR["@"]] * 7):
        c.write("wPartyMonOTs", b, i)


MALE, FEMALE = 0xEF, 0xF5


def build_row(c, name, level=5, gender=0, status=0):
    """Build one row and return its tiles and the tile count it reported.

    The gender goes in b and the status in c, which is why this uses call()
    rather than farcall(): farcall owns a and hl and cannot pass either.
    """
    for i, b in enumerate(encode(name)):
        c.write("wEnemyMonNickname", b, i)
    c.write("wEnemyMonLevel", level)
    c.write("wEnemyMonStatus", status)
    c.call("PlusHUDBuildEnemyRow", b=gender, c=status)
    tiles = c.read_block("wPlusHUDRow", ROW_BYTES)
    return tiles, c.pb.register_file.B


def ink_columns(row):
    """Pixel columns that have ink in them, across the whole eleven tile row."""
    cols = set()
    for tile in range(PLUS_HUD_TILES):
        for y in range(8):
            byte = row[tile * TILE_1BPP_SIZE + y]
            for bit in range(8):
                if byte & (0x80 >> bit):
                    cols.add(tile * 8 + bit)
    return cols


def tail_width(level, gender, status):
    """Pixels taken by everything after the name."""
    w = PLUS_HUD_WIDE_W if gender else 0
    if status or level >= 10:
        return w + 3 * PLUS_HUD_WIDE_W     # ":L" and two digits, or three, or a status
    return w + 2 * PLUS_HUD_WIDE_W         # ":L" and one digit


def test_layout(c):
    print("\n== the whole row is set against the right, with no gaps ==")
    right = PLUS_HUD_ALIGN_TILES * 8
    for name, level, gender in (("PSYDUCK", 14, MALE), ("NIDOKING", 45, FEMALE),
                                ("MR.MIME", 7, 0), ("Sparky", 3, MALE),
                                ("Mew", 5, 0), ("FARFETCH'D", 50, MALE)):
        row, tiles = build_row(c, name, level=level, gender=gender)
        cols = ink_columns(row)
        width = len(name) * PLUS_HUD_GLYPH_W + tail_width(level, gender, 0)
        if width > right:
            # too wide to set right, so it starts at the left and runs into
            # the eleventh tile instead of overlapping itself
            check(min(cols) == 0 and max(cols) < PLUS_HUD_TILES * 8,
                  f"{name} L{level} is too wide to set right, so it starts left",
                  f"ink {min(cols)}..{max(cols)}, width {width}")
        else:
            check(right - PLUS_HUD_WIDE_W < max(cols) < right,
                  f"{name} L{level} finishes against the right",
                  f"last inked column {max(cols)}, wanted just under {right}")
            check(min(cols) >= right - width,
                  f"{name} L{level} starts no earlier than its own width allows",
                  f"first inked column {min(cols)}, width {width}")
        # nothing inside the row is more than a glyph apart, so there is no
        # gap between the name, the symbol and the level
        run = worst = 0
        for x in range(min(cols), max(cols)):
            run = run + 1 if x not in cols else 0
            worst = max(worst, run)
        check(worst < PLUS_HUD_GLYPH_W,
              f"{name} L{level} has no gap inside it",
              f"longest blank run {worst}")
        wanted = PLUS_HUD_TILES if width > right else PLUS_HUD_ALIGN_TILES
        check(tiles == wanted,
              f"{name} L{level} reports the {wanted} tiles it filled",
              f"reported {tiles}")


def test_worst_case(c):
    print("\n== the worst case still fits the row ==")
    row, tiles = build_row(c, "ABCDEFGHIJ", level=100, gender=MALE)
    cols = ink_columns(row)
    check(tiles <= PLUS_HUD_TILES,
          "ten characters, a gender symbol and level 100 fit eleven tiles",
          f"needed {tiles}, has {PLUS_HUD_TILES}")
    check(max(cols) < PLUS_HUD_TILES * 8,
          "and nothing runs past the end of the row",
          f"last inked column {max(cols)}")
    # 50 pixels of name and 32 of tail is two more than the ten tiles the row
    # is normally set against, so this one case starts at the left instead
    check(min(cols) == 0,
          "a row too wide to set right starts at the left",
          f"first inked column {min(cols)}")


def test_gender_and_level(c):
    print("\n== the level lands in the same place every time ==")
    right = PLUS_HUD_ALIGN_TILES * 8
    male, _ = build_row(c, "PSYDUCK", level=14, gender=MALE)
    female, _ = build_row(c, "PSYDUCK", level=14, gender=FEMALE)
    check(male != female, "the two gender symbols are different glyphs")
    check(max(ink_columns(male)) == max(ink_columns(female)),
          "and both end in the same place",
          f"{max(ink_columns(male))} against {max(ink_columns(female))}")
    for level in (5, 14, 99, 100):
        row, _ = build_row(c, "PSYDUCK", level=level, gender=MALE)
        check(right - PLUS_HUD_WIDE_W < max(ink_columns(row)) <= right,
              f"level {level} finishes against the right",
              f"last inked column {max(ink_columns(row))}")
    long_name, _ = build_row(c, "NIDOKING", level=14, gender=MALE)
    short_name, _ = build_row(c, "Mew", level=14, gender=MALE)
    check(max(ink_columns(long_name)) == max(ink_columns(short_name)),
          "and in the same place whatever the name's length",
          f"{max(ink_columns(long_name))} against {max(ink_columns(short_name))}")
    # a shorter name pushes the row right, it does not stretch it
    check(min(ink_columns(short_name)) > min(ink_columns(long_name)),
          "a shorter name starts further right, rather than leaving a gap",
          f"{min(ink_columns(short_name))} against {min(ink_columns(long_name))}")


def test_status(c):
    print("\n== a status condition replaces the level ==")
    SLP, PSN, BRN, FRZ, PAR = 0x07, 1 << 3, 1 << 4, 1 << 5, 1 << 6
    lvl, _ = build_row(c, "PSYDUCK", level=14)
    seen = {}
    for name, bits in (("SLP", SLP), ("PSN", PSN), ("BRN", BRN),
                       ("FRZ", FRZ), ("PAR", PAR)):
        row, _ = build_row(c, "PSYDUCK", level=14, status=bits)
        seen[name] = row
        check(row != lvl, f"{name} is drawn instead of the level")
        check(max(ink_columns(row)) <= PLUS_HUD_ALIGN_TILES * 8,
              f"{name} is set against the right like the level",
              f"last inked column {max(ink_columns(row))}")
    check(len(set(map(bytes, seen.values()))) == 5,
          "all five status strings are different",
          f"{len(set(map(bytes, seen.values())))} distinct")


def test_unknown_character(c):
    print("\n== a character with no glyph is skipped ==")
    plain = ink_columns(build_row(c, "ABC", level=5)[0])
    # $6e is the combined ":L" tile, which the narrow font has no glyph for
    for i, b in enumerate([CHAR["A"], CHAR["B"], 0x6E, CHAR["C"], CHAR["@"]]):
        c.write("wEnemyMonNickname", b, i)
    c.call("PlusHUDBuildEnemyRow")
    odd = ink_columns(c.read_block("wPlusHUDRow", ROW_BYTES))
    # the row is right aligned, so a skipped character widens it leftwards
    check(min(odd) < min(plain),
          "an unknown character takes up room without drawing",
          f"starts at {min(odd)} against {min(plain)}")


def reach_battle(c):
    """Walk the Goldenrod save into the Route 34 trainer and stop with both
    HUDs on screen. Shared with battle_now.py so the two cannot drift apart."""
    c.continue_game()
    give_party_mon(c)
    for _ in range(8):
        c.press("down", hold=20, release=14)
    for _ in range(40):
        c.press("a", hold=12, release=12)
        c.run(45)
        if c.read("wBattleMode"):
            break
    else:
        return False
    # the player's mon is sent out last, so its row appearing means both are up
    tm = c.pb.tilemap_background
    for _ in range(30):
        c.press("a", hold=10, release=10)
        c.run(40)
        if tm[9, 8] & 0xFF == PLAYER_TILES[0]:
            break
    return True


def test_in_battle():
    print("\n== both HUDs point at their composed tiles in a battle ==")
    with Crystal(sav=os.path.join(STATES, "fps60.sav")) as c:
        started = reach_battle(c)
        check(started, "a battle started", "wBattleMode stayed 0")
        if not started:
            return
        tm = c.pb.tilemap_background

        def row_of(x0, y, ids):
            out = []
            for x in range(x0, x0 + PLUS_HUD_TILES):
                t = tm[x, y] & 0xFF
                if len(out) >= len(ids) or t != ids[len(out)]:
                    break
                out.append(t)
            return out

        enemy = row_of(1, 1, ENEMY_TILES)
        check(len(enemy) >= 4,
              "the enemy row is a run of its own composed tiles",
              f"only {len(enemy)}: {[f'{t:02x}' for t in enemy]}")
        player = row_of(9, 8, PLAYER_TILES)
        check(len(player) >= 4,
              "the player row is a run of its own composed tiles",
              f"only {len(player)}: {[f'{t:02x}' for t in player]}")

        # the whole row is composed now, so no ordinary font tile appears in it
        tail = [tm[x, 1] & 0xFF for x in range(1 + len(enemy), 12)]
        check(all(t == 0x7F for t in tail),
              "nothing after the composed run, so the level is inside it",
              f"{[f'{t:02x}' for t in tail]}")

        # the name came down onto the bar rather than the bar moving up, so
        # every other part of the HUD is still where vanilla put it
        check(tm[2, 2] & 0xFF != 0x7F,
              "the enemy HP bar is directly below the name, in its vanilla row",
              f"tile at (2,2) is {tm[2, 2] & 0xFF:02x}")
        check(tm[10, 9] & 0xFF != 0x7F,
              "the player HP bar is still in its vanilla row",
              f"tile at (10,9) is {tm[10, 9] & 0xFF:02x}")

        shot = os.path.join(tempfile.gettempdir(), "plus_hud.png")
        c.screenshot(shot)
        print(f"  screenshot: {shot}")


def main():
    with Crystal() as c:
        c.run(400)
        test_layout(c)
        test_worst_case(c)
        test_gender_and_level(c)
        test_status(c)
        test_unknown_character(c)
    test_in_battle()

    print()
    if failures:
        print(f"{len(failures)} FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
