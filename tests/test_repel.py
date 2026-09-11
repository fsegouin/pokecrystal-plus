"""Repel price, mart stock and top-off (Crystal+).

Prices and mart lists are read straight out of the ROM. The top-off routines
are then driven one at a time on a live overworld, and the last group walks
real steps on Route 34 to watch the offer, a yes, a no and the silent renewal
play out through the game's own step counter.

Calling a routine directly parks the CPU in a loop the game never leaves, so
the walking group gets a game of its own.

Needs tests/states/chain0.sav, which tests/make_chain_save.py writes.

Run: .venv/bin/python tests/test_repel.py
"""
import os
import re
import sys

from harness import ROOT, STATES, Crystal

SAVE = os.path.join(STATES, "chain0.sav")

PLUS_REPEL_KIND_LO_F = 5
KIND_MASK = 0b11 << PLUS_REPEL_KIND_LO_F
AUTO = 1 << 7
KINDS = ["REPEL", "SUPER_REPEL", "MAX_REPEL"]  # kind 1, 2, 3
STEPS = {"REPEL": 100, "SUPER_REPEL": 200, "MAX_REPEL": 250}
INDOOR = 3
ITEMATTR_STRUCT_LENGTH = 7
MART_BUFFER = 15  # wCurMartItems

# The marts a player stocks up at for the road. The others sell TMs,
# vitamins, battle items, mail, souvenirs or herbs.
GENERAL_MARTS = [
    "MART_CHERRYGROVE", "MART_CHERRYGROVE_DEX", "MART_VIOLET", "MART_AZALEA",
    "MART_CIANWOOD", "MART_GOLDENROD_2F_2", "MART_OLIVINE", "MART_ECRUTEAK",
    "MART_MAHOGANY_2", "MART_BLACKTHORN", "MART_VIRIDIAN", "MART_PEWTER",
    "MART_CERULEAN", "MART_LAVENDER", "MART_VERMILION", "MART_CELADON_2F_1",
    "MART_FUCHSIA", "MART_SAFFRON", "MART_MT_MOON", "MART_INDIGO_PLATEAU",
]


def source(*path):
    return open(os.path.join(ROOT, *path), encoding="utf-8").read()


def item_ids():
    return {m.group(1): int(m.group(2), 16) for m in re.finditer(
        r"^\s*const\s+(\w+)\s*;\s*([0-9a-f]{2})\b",
        source("constants", "item_constants.asm"), re.M | re.I)}


def mart_ids():
    names = re.findall(r"^\s*const\s+(MART_\w+)", source("constants", "mart_constants.asm"), re.M)
    return {name: i for i, name in enumerate(names)}


def map_ids():
    maps, group = {}, None
    for line in source("constants", "map_constants.asm").splitlines():
        m = re.match(r"\s*newgroup\s+\w+\s*;\s*(\d+)", line)
        if m:
            group = int(m.group(1))
        m = re.match(r"\s*map_const\s+(\w+),.*;\s*(\d+)", line)
        if m:
            maps[m.group(1)] = (group, int(m.group(2)))
    return maps


def charmap():
    table = {}
    for m in re.finditer(r'^\s*charmap\s+"(.)",\s*\$([0-9a-f]{2})', source("constants", "charmap.asm"),
                         re.M | re.I):
        table.setdefault(int(m.group(2), 16), m.group(1))
    return table


ITEMS = item_ids()
CHARS = charmap()


class Checks:
    def __init__(self):
        self.failures = []

    def __call__(self, label, got, want):
        ok = got == want
        if not ok:
            self.failures.append(label)
        print(f"  {'ok  ' if ok else 'FAIL'} {label}: got {got!r}, want {want!r}")


def set_bag(c, pairs):
    c.write("wNumItems", len(pairs))
    for i, (name, qty) in enumerate(pairs):
        c.write("wItems", ITEMS[name], offset=2 * i)
        c.write("wItems", qty, offset=2 * i + 1)
    c.write("wItems", 0xFF, offset=2 * len(pairs))


def bag(c):
    names = {v: k for k, v in ITEMS.items()}
    return [(names.get(c.read("wItems", 2 * i), "?"), c.read("wItems", 2 * i + 1))
            for i in range(c.read("wNumItems"))]


def set_state(c, kind, auto, others=0):
    """kind is 0 for none or a KINDS name; others fills the bits below."""
    k = 0 if not kind else KINDS.index(kind) + 1
    c.write("wPlusFlags", others | (k << PLUS_REPEL_KIND_LO_F) | (AUTO if auto else 0))


def state(c):
    f = c.read("wPlusFlags")
    k = (f & KIND_MASK) >> PLUS_REPEL_KIND_LO_F
    return (KINDS[k - 1] if k else None), bool(f & AUTO)


def screen(c):
    return "".join(CHARS.get(c.read("wTilemap", i), " ") for i in range(20 * 18))


def check_rom(c, check):
    print("repels cost $1")
    for name in KINDS:
        off = (ITEMS[name] - 1) * ITEMATTR_STRUCT_LENGTH
        check(f"{name} price", c.read("ItemAttributes", off) | c.read("ItemAttributes", off + 1) << 8, 1)

    print("every general mart sells a repel")
    bank = c.bank("Marts")
    repels = {ITEMS[n] for n in KINDS}
    for name, idx in mart_ids().items():
        ptr = c.read16("Marts", 2 * idx)
        count = c.pb.memory[bank, ptr]
        stock = []
        while (item := c.pb.memory[bank, ptr + 1 + len(stock)]) != 0xFF:
            stock.append(item)
        if count != len(stock) or count > MART_BUFFER:
            check(f"{name} count byte matches and fits", (count, len(stock)), (len(stock), len(stock)))
        if name in GENERAL_MARTS:
            check(f"{name} stocks a repel", bool(repels & set(stock)), True)


def check_routines(c, check):
    print("using a repel remembers its kind and leaves auto-renew off")
    for name in KINDS:
        set_state(c, None, True, others=0b11111)
        c.write("wCurItem", ITEMS[name])
        c.call("PlusRepelUsed")
        check(f"{name} used", state(c), (name, False))
    check("the other flags survive", c.read("wPlusFlags") & 0b11111, 0b11111)

    print("auto-renew")
    set_state(c, "REPEL", False)
    set_bag(c, [("REPEL", 2)])
    c.write("wRepelEffect", 0)
    c.call("PlusRepelAutoRenew")
    check("off: nothing used", (c.read("wRepelEffect"), bag(c)), (0, [("REPEL", 2)]))

    set_state(c, "SUPER_REPEL", True)
    set_bag(c, [("POTION", 1), ("SUPER_REPEL", 2), ("REPEL", 5)])
    c.call("PlusRepelAutoRenew")
    check("on: the same kind first", c.read("wRepelEffect"), STEPS["SUPER_REPEL"])
    check("on: one used", bag(c), [("POTION", 1), ("SUPER_REPEL", 1), ("REPEL", 5)])
    check("on: stays on", state(c), ("SUPER_REPEL", True))

    set_state(c, "SUPER_REPEL", True)
    set_bag(c, [("MAX_REPEL", 1), ("REPEL", 1)])
    c.write("wRepelEffect", 0)
    c.call("PlusRepelAutoRenew")
    check("none of that kind: the weakest instead", c.read("wRepelEffect"), STEPS["REPEL"])
    check("the last one leaves the pocket", bag(c), [("MAX_REPEL", 1)])
    check("and becomes the kind", state(c), ("REPEL", True))

    set_state(c, None, True)
    set_bag(c, [("MAX_REPEL", 1), ("SUPER_REPEL", 1)])
    c.write("wRepelEffect", 0)
    c.call("PlusRepelAutoRenew")
    check("no kind yet: the weakest", c.read("wRepelEffect"), STEPS["SUPER_REPEL"])

    set_state(c, "MAX_REPEL", True)
    set_bag(c, [("POTION", 3)])
    c.write("wRepelEffect", 0)
    c.call("PlusRepelAutoRenew")
    check("out of repels: switches off", (c.read("wRepelEffect"), state(c)), (0, ("MAX_REPEL", False)))
    check("out of repels: pack untouched", bag(c), [("POTION", 3)])

    print("the offer")
    set_state(c, "REPEL", False)
    set_bag(c, [("POTION", 1), ("MAX_REPEL", 1)])
    c.call("PlusRepelCheckRefill")
    name = ""
    for i in range(12):
        b = c.read("wStringBuffer1", i)
        if b == 0x50:
            break
        name += CHARS.get(b, "?")
    check("offered with one in the pack", (c.read("wScriptVar"), name), (1, "MAX REPEL"))
    set_bag(c, [("POTION", 1)])
    c.call("PlusRepelCheckRefill")
    check("not offered without", c.read("wScriptVar"), 0)

    set_state(c, "REPEL", False)
    set_bag(c, [("REPEL", 3)])
    c.write("wRepelEffect", 0)
    c.call("PlusRepelTopOff")
    check("yes uses one", (c.read("wRepelEffect"), bag(c)), (STEPS["REPEL"], [("REPEL", 2)]))
    check("yes switches auto-renew on", state(c), ("REPEL", True))

    print("only a building ends auto-renew")
    maps = map_ids()
    home = (c.read("wMapGroup"), c.read("wMapNumber"))
    for name in ("PLAYERS_HOUSE_2F", "ROUTE_34", "DARK_CAVE_VIOLET_ENTRANCE", "ROUTE_34_ILEX_FOREST_GATE"):
        group, number = maps[name]
        c.write("wMapGroup", group)
        c.write("wMapNumber", number)
        c.call("GetMapEnvironment")
        indoor = c.pb.register_file.A == INDOOR
        set_state(c, "SUPER_REPEL", True)
        c.call("PlusRepelEnterMap")
        check(f"{name} ({'indoor' if indoor else 'not indoor'})", state(c), ("SUPER_REPEL", not indoor))
    c.write("wMapGroup", home[0])
    c.write("wMapNumber", home[1])

    print("DoRepelStep")
    carry = lambda: bool(c.pb.register_file.F & 0x10)  # noqa: E731
    set_state(c, "REPEL", True)
    set_bag(c, [("REPEL", 2)])
    c.write("wRepelEffect", 5)
    c.call("DoRepelStep")
    check("a step off the count", (c.read("wRepelEffect"), carry()), (4, False))

    c.write("wScriptRunning", 0)
    c.write("wRepelEffect", 1)
    c.call("DoRepelStep")
    check("auto-renew: renewed, step counted", (c.read("wRepelEffect"), carry()), (STEPS["REPEL"], False))
    check("auto-renew: no script", c.read("wScriptRunning"), 0)
    check("auto-renew: one used", bag(c), [("REPEL", 1)])

    set_state(c, "REPEL", False)
    c.write("wRepelEffect", 1)
    c.call("DoRepelStep")
    bank, addr = c.syms["PlusRepelWoreOffScript"]
    check("otherwise the script runs",
          (carry(), c.read("wScriptBank"), c.read16("wScriptPos")), (True, bank, addr))
    check("and nothing is used yet", bag(c), [("REPEL", 1)])


def take_step(c):
    """Walk one tile in whichever direction is open. True once moved."""
    for d in ("left", "right", "up", "down"):
        before = (c.read("wXCoord"), c.read("wYCoord"))
        c.press(d, hold=16, release=24)
        if (c.read("wXCoord"), c.read("wYCoord")) != before:
            return True
    return False


def wait_for(c, text, limit=40):
    """Advance text with A until `text` is on screen. Returns the screen."""
    for _ in range(limit):
        shown = screen(c)
        if text in shown:
            return shown
        c.press("a", hold=6, release=14)
    return screen(c)


def mash(c, button, presses=10):
    for _ in range(presses):
        c.press(button, hold=6, release=20)


def check_walking(c, check):
    print("walking on Route 34")
    set_state(c, "REPEL", False)
    set_bag(c, [("POTION", 1), ("REPEL", 3)])
    c.write("wRepelEffect", 1)
    check("a step is taken", take_step(c), True)
    shown = wait_for(c, "REPEL?")
    check("the offer names the repel", "Use another" in shown and "REPEL?" in shown, True)
    mash(c, "a")
    check("yes: topped off", (c.read("wRepelEffect"), bag(c)), (STEPS["REPEL"], [("POTION", 1), ("REPEL", 2)]))
    check("yes: auto-renew on", state(c), ("REPEL", True))

    c.write("wRepelEffect", 1)
    check("the next expiry is walked through", take_step(c), True)
    c.run(30)
    check("renewed without a word", (c.read("wRepelEffect"), bag(c)),
          (STEPS["REPEL"], [("POTION", 1), ("REPEL", 1)]))
    check("and the player walks straight on", take_step(c), True)
    check("counting down again", c.read("wRepelEffect"), STEPS["REPEL"] - 1)

    set_state(c, "REPEL", False)
    c.write("wRepelEffect", 1)
    check("a step is taken", take_step(c), True)
    wait_for(c, "REPEL?")
    mash(c, "b")
    check("no: nothing used", (c.read("wRepelEffect"), bag(c)), (0, [("POTION", 1), ("REPEL", 1)]))
    check("no: auto-renew stays off", state(c), ("REPEL", False))

    set_bag(c, [("POTION", 1)])
    c.write("wRepelEffect", 1)
    check("a step is taken", take_step(c), True)
    shown = wait_for(c, "wore off.")
    check("without a repel: just the vanilla message", "wore off." in shown and "Use another" not in shown, True)
    mash(c, "a", presses=4)
    check("and the player walks on", take_step(c), True)


def main():
    if not os.path.exists(SAVE):
        print(f"missing {os.path.relpath(SAVE, ROOT)}: run tests/make_chain_save.py first")
        return 1
    check = Checks()
    with Crystal(sav=SAVE) as c:
        c.continue_game()
        check_walking(c, check)
    with Crystal(sav=SAVE) as c:
        c.continue_game()
        check_rom(c, check)
        check_routines(c, check)

    print()
    if check.failures:
        print(f"{len(check.failures)} failure(s): {', '.join(check.failures)}")
        return 1
    print("all repel checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
