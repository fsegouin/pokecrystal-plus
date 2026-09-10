"""Checks for the wild encounter randomizer.

Most of these drive the plus routines directly rather than through gameplay:
the maps are pure functions of wPlusSeed and wPlusFlags, so poking those two
and running PlusBuildWildMaps covers far more ground than walking into grass
would. The last group does walk into grass, to prove the hooks are wired up.

    .venv/bin/python tests/test_wild.py
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harness import Crystal  # noqa: E402

NUM_POKEMON = 251
UNOWN = 201

# wPlusFlags
PLUS_WILD_ENABLED_F = 0
PLUS_WILD_MODE_SHIFT = 1
MODE_TIERED, MODE_UNTIERED, MODE_CHAOS = 0, 1, 2

# Two bytes of "jr -2": park the CPU here when a hijacked routine returns.
LANDING_PAD = 0xFFF0


def flags(mode=None):
    if mode is None:
        return 0
    return (1 << PLUS_WILD_ENABLED_F) | (mode << PLUS_WILD_MODE_SHIFT)


class Runner:
    """Boots the ROM and calls plus routines directly.

    The game itself never resumes: each call parks the CPU in a two byte
    loop in HRAM, and the next call hijacks it again from there. Only WRAM
    contents matter to these checks, and nothing in the game is running to
    disturb them.
    """

    def __init__(self):
        self.c = Crystal()
        self.c.run(600)
        # Mashing A walks the whole new game flow: title, Oak, gender, name.
        for _ in range(400):
            self.c.press("A")
            self.c.run(12)
        assert (self.c.read("wMapGroup"), self.c.read("wMapNumber")) == (24, 7), \
            "the new game flow did not end up in the player's bedroom"
        self.new_game_seed = self.c.read16("wPlusSeed")
        self.new_game_flags = self.c.read("wPlusFlags")
        pb = self.c.pb
        pb.memory[0xFFFF] = 0  # no interrupts while we are driving
        pb.memory[LANDING_PAD] = 0x18
        pb.memory[LANDING_PAD + 1] = 0xFE
        self.tiers = self._read_tiers()

    def close(self):
        self.c.stop()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def call(self, symbol, **regs):
        """Run a routine to completion. Returns the register file."""
        pb = self.c.pb
        rf = pb.register_file
        bank, addr = self.c.syms[symbol]
        pb.memory[0x2000] = bank
        # hROMBank shadows the MBC register, and farcall restores the bank
        # from it rather than from the cartridge, so keep the two in step.
        pb.memory[self.c.addr("hROMBank")] = bank
        for name, value in regs.items():
            setattr(rf, name, value)
        sp = (rf.SP - 2) & 0xFFFF
        pb.memory[sp] = LANDING_PAD & 0xFF
        pb.memory[sp + 1] = LANDING_PAD >> 8
        rf.SP = sp
        rf.PC = addr
        for _ in range(30):
            pb.tick(1, render=False)
            if rf.PC in (LANDING_PAD, LANDING_PAD + 1):
                return rf
        raise RuntimeError(f"{symbol} did not return within 30 frames")

    def _read_list(self, symbol):
        bank, addr = self.c.syms[symbol]
        out = []
        while True:
            v = self.c.pb.memory[bank, addr]
            if v == 0xFF:
                return out
            out.append(v)
            addr += 1

    def _read_tiers(self):
        # PlusTierC runs straight into PlusTierStarter, so reading from
        # PlusTierC to the first terminator gives the whole C tier.
        return {
            "C": self._read_list("PlusTierC"),
            "starter": self._read_list("PlusTierStarter"),
            "B": self._read_list("PlusTierB"),
            "A": self._read_list("PlusTierA"),
        }

    def build(self, seed, mode=None):
        self.c.write("wPlusSeed", seed & 0xFF)
        self.c.write("wPlusSeed", seed >> 8, offset=1)
        self.c.write("wPlusFlags", flags(mode))
        self.call("PlusBuildWildMaps")

    def forward(self):
        return list(self.c.read_block("wPlusWildMap", NUM_POKEMON + 1))

    def inverse(self):
        return list(self.c.read_block("wPlusWildInverseMap", NUM_POKEMON + 1))

    def map_species(self, species):
        # b in, b out: farcall cannot carry a value in a, so the plus
        # routines pass species through b instead.
        return self.call("PlusMapWildSpecies", B=species).B

    def map_starter(self, species):
        return self.call("PlusMapStarterSpecies", A=species).A


CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


# The pool the shuffle modes permute. Everything else must map to itself.
def pool(r, mode):
    t = r.tiers
    if mode == MODE_TIERED:
        return [t["C"] + t["starter"], t["B"], t["A"]]
    return [t["C"] + t["starter"] + t["B"] + t["A"]]


def assert_permutation(fwd, label):
    body = fwd[1:NUM_POKEMON + 1]
    assert sorted(body) == list(range(1, NUM_POKEMON + 1)), \
        f"{label}: wPlusWildMap is not a permutation of 1..{NUM_POKEMON}"
    assert fwd[0] == 0, f"{label}: entry 0 should stay 0"


@check
def disabled_is_vanilla(r):
    r.build(0x1234, mode=None)
    fwd = r.forward()
    assert fwd == list(range(NUM_POKEMON + 1)), "disabled must leave the identity map"
    for s in (1, 25, 100, UNOWN, NUM_POKEMON):
        assert r.map_species(s) == s, f"disabled must not remap {s}"


@check
def no_seed_is_vanilla(r):
    # An old save has no seed, so there is no pattern to rebuild.
    r.c.write("wPlusSeed", 0)
    r.c.write("wPlusSeed", 0, offset=1)
    r.c.write("wPlusFlags", flags(MODE_UNTIERED))
    r.call("PlusBuildWildMaps")
    assert r.forward() == list(range(NUM_POKEMON + 1)), "a zero seed must stay identity"
    assert r.c.read("wPlusFlags") == 0, "a zero seed must clear wPlusFlags"


@check
def tiered_keeps_tiers(r):
    for seed in (0x0001, 0x1234, 0xBEEF, 0xFFFF):
        r.build(seed, MODE_TIERED)
        fwd = r.forward()
        assert_permutation(fwd, f"tiered seed {seed:#06x}")
        covered = set()
        for group in pool(r, MODE_TIERED):
            members = set(group)
            covered |= members
            images = {fwd[s] for s in group}
            assert images == members, \
                f"tiered seed {seed:#06x}: a tier's members left their tier"
        for s in range(1, NUM_POKEMON + 1):
            if s not in covered:
                assert fwd[s] == s, \
                    f"tiered seed {seed:#06x}: {s} is outside the pool but moved"


@check
def untiered_permutes_the_union(r):
    for seed in (0x0001, 0x4d2, 0xC0DE, 0xFFFF):
        r.build(seed, MODE_UNTIERED)
        fwd = r.forward()
        assert_permutation(fwd, f"untiered seed {seed:#06x}")
        members = set(pool(r, MODE_UNTIERED)[0])
        images = {fwd[s] for s in members}
        assert images == members, \
            f"untiered seed {seed:#06x}: the pool is not closed under the map"
        for s in range(1, NUM_POKEMON + 1):
            if s not in members:
                assert fwd[s] == s, \
                    f"untiered seed {seed:#06x}: {s} is outside the pool but moved"


@check
def unown_never_moves(r):
    for mode in (MODE_TIERED, MODE_UNTIERED, MODE_CHAOS):
        r.build(0x1234, mode)
        assert r.forward()[UNOWN] == UNOWN, f"mode {mode}: Unown moved in the map"
        assert r.map_species(UNOWN) == UNOWN, f"mode {mode}: Unown was remapped"
        assert r.map_species(0) == 0, f"mode {mode}: an empty slot was filled in"


@check
def inverse_undoes_the_map(r):
    for mode in (MODE_TIERED, MODE_UNTIERED):
        for seed in (0x1234, 0xABCD):
            r.build(seed, mode)
            fwd, inv = r.forward(), r.inverse()
            for s in range(1, NUM_POKEMON + 1):
                assert inv[fwd[s]] == s, \
                    f"mode {mode} seed {seed:#06x}: inverse is wrong at {s}"
            assert inv[0] == 0, "inverse entry 0 should stay 0"


@check
def same_seed_same_maps(r):
    r.build(0x7A11, MODE_TIERED)
    first = r.forward()
    # Rebuild over a different pattern to prove nothing is carried over.
    r.build(0x0042, MODE_UNTIERED)
    r.build(0x7A11, MODE_TIERED)
    assert r.forward() == first, "the same seed gave two different maps"


@check
def different_seeds_differ(r):
    r.build(0x1111, MODE_UNTIERED)
    a = r.forward()
    r.build(0x2222, MODE_UNTIERED)
    assert r.forward() != a, "two seeds produced the same map"


@check
def map_lookup_matches_the_table(r):
    r.build(0x5EED, MODE_TIERED)
    fwd = r.forward()
    for s in (1, 7, 25, 60, 129, 150, 200, 249, NUM_POKEMON):
        assert r.map_species(s) == fwd[s], f"PlusMapWildSpecies disagrees at {s}"


@check
def map_preserves_registers(r):
    r.build(0x5EED, MODE_UNTIERED)
    rf = r.call("PlusMapWildSpecies", B=25, C=0x11, D=0x22, E=0x33, HL=0x4455)
    assert rf.C == 0x11, "PlusMapWildSpecies clobbered c"
    assert rf.D == 0x22, "PlusMapWildSpecies clobbered d"
    assert rf.E == 0x33, "PlusMapWildSpecies clobbered e"
    assert rf.HL == 0x4455, "PlusMapWildSpecies clobbered hl"


@check
def chaos_leaves_the_table_alone(r):
    # Chaos has no permutation, so AREA and everything else fall back to
    # vanilla behaviour through the identity map.
    r.build(0x1234, MODE_CHAOS)
    assert r.forward() == list(range(NUM_POKEMON + 1)), "chaos must not build a map"
    assert r.inverse() == list(range(NUM_POKEMON + 1)), "chaos must not build an inverse"


@check
def chaos_never_rolls_a_banned_species(r):
    banned = set(r._read_list("PlusChaosBans"))
    assert len(banned) == 12, f"expected 12 banned species, got {len(banned)}"
    r.build(0x1234, MODE_CHAOS)
    seen = set()
    for _ in range(400):
        got = r.map_species(19)  # Rattata, a Route 29 slot
        assert 1 <= got <= NUM_POKEMON, f"chaos rolled {got}, outside 1..{NUM_POKEMON}"
        assert got not in banned, f"chaos rolled banned species {got}"
        seen.add(got)
    assert len(seen) > 50, f"chaos only ever rolled {len(seen)} species; is it rolling?"


@check
def starters_are_distinct_and_stable(r):
    balls = (155, 158, 152)  # Cyndaquil, Totodile, Chikorita
    legal = set(r.tiers["starter"])
    for seed in (0x0001, 0x1234, 0xBEEF, 0xFFFF, 0x8000):
        r.build(seed, MODE_TIERED)
        got = [r.map_starter(b) for b in balls]
        assert len(set(got)) == 3, f"seed {seed:#06x}: two balls hold the same mon"
        for s in got:
            assert s in legal, f"seed {seed:#06x}: {s} is not starter legal"
        # Looking at a ball twice must not reshuffle the table.
        again = [r.map_starter(b) for b in balls]
        assert again == got, f"seed {seed:#06x}: the offer moved between looks"


@check
def starters_are_vanilla_when_disabled(r):
    r.build(0x1234, mode=None)
    for ball in (155, 158, 152):
        assert r.map_starter(ball) == ball, "disabled must leave the starters alone"


@check
def starters_follow_the_seed(r):
    r.build(0x1111, MODE_TIERED)
    a = [r.map_starter(b) for b in (155, 158, 152)]
    r.build(0x2222, MODE_TIERED)
    assert [r.map_starter(b) for b in (155, 158, 152)] != a, \
        "two seeds offered the same three starters"


@check
def non_starters_pass_through(r):
    r.build(0x1234, MODE_TIERED)
    for s in (1, 25, UNOWN, NUM_POKEMON):
        assert r.map_starter(s) == s, f"the starter map should ignore {s}"


# Gameplay level checks. These call the vanilla encounter routines in place,
# so they exercise the hook sites rather than the plus code on its own.

ROUTE_29 = (24, 3)
TIME_DAY = 1
PLAYER_NORMAL = 0


def route_29_day_slots():
    """The seven day slots on Route 29, as (level, species) from the source."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ids = {}
    n = 0
    with open(os.path.join(root, "constants/pokemon_constants.asm")) as f:
        for line in f:
            line = line.strip()
            if line.startswith("const ") and not line.startswith("const_def"):
                n += 1
                ids[line.split()[1].split(";")[0]] = n
    slots = []
    with open(os.path.join(root, "data/wild/johto_grass.asm")) as f:
        block = False
        for line in f:
            t = line.strip()
            if t.startswith("def_grass_wildmons ROUTE_29"):
                block = True
                continue
            if block:
                if t.startswith("end_grass_wildmons"):
                    break
                if t.startswith("db ") and "," in t and "percent" not in t:
                    lvl, mon = (x.strip() for x in t[3:].split(";")[0].split(","))
                    slots.append((int(lvl), ids[mon]))
    assert len(slots) == 21, f"expected 21 Route 29 slots, parsed {len(slots)}"
    return slots[7:14]


def encounters(r, trials=150):
    """Run ChooseWildEncounter on Route 29 and collect (level, species)."""
    r.c.write("wMapGroup", ROUTE_29[0])
    r.c.write("wMapNumber", ROUTE_29[1])
    r.c.write("wTimeOfDay", TIME_DAY)
    r.c.write("wPlayerState", PLAYER_NORMAL)
    out = []
    for _ in range(trials):
        r.c.write("wTempWildMonSpecies", 0)
        r.c.write("wCurPartyLevel", 0)
        r.call("ChooseWildEncounter")
        sp = r.c.read("wTempWildMonSpecies")
        if sp:
            out.append((r.c.read("wCurPartyLevel"), sp))
    assert len(out) > trials // 2, "hardly any encounters came back"
    return out


@check
def new_game_rolls_a_pattern(r):
    assert r.new_game_seed != 0, "a new game must leave a nonzero wPlusSeed"
    assert r.new_game_flags == 0, "a new game must leave every feature off"


@check
def grass_is_vanilla_when_disabled(r):
    vanilla = set(route_29_day_slots())
    r.build(0x1234, mode=None)
    for pair in encounters(r):
        assert pair in vanilla, f"disabled gave {pair}, not a Route 29 day slot"


@check
def grass_keeps_the_level_and_takes_the_mapped_species(r):
    vanilla = route_29_day_slots()
    for mode in (MODE_TIERED, MODE_UNTIERED):
        r.build(0xBEEF, mode)
        fwd = r.forward()
        allowed = {(lvl, fwd[sp]) for lvl, sp in vanilla}
        got = set(encounters(r))
        assert got <= allowed, \
            f"mode {mode}: {got - allowed} is not a mapped Route 29 day slot"
        assert got != set(vanilla), f"mode {mode}: nothing was actually shuffled"
        assert {lvl for lvl, _ in got} == {lvl for lvl, _ in vanilla}, \
            f"mode {mode}: the levels changed"


@check
def grass_chaos_stays_in_bounds(r):
    banned = set(r._read_list("PlusChaosBans"))
    levels = {lvl for lvl, _ in route_29_day_slots()}
    r.build(0xBEEF, MODE_CHAOS)
    got = encounters(r)
    for lvl, sp in got:
        assert lvl in levels, f"chaos changed a level: {lvl}"
        assert sp not in banned, f"chaos gave banned species {sp}"
        assert 1 <= sp <= NUM_POKEMON, f"chaos gave species {sp}"
    assert len({sp for _, sp in got}) > 20, "chaos is not rolling freely"


@check
def headbutt_species_are_mapped(r):
    # Read the Route treemon tables straight out of the ROM: the rarest
    # slots are 5%, so sampling alone would not cover them.
    bank, addr = r.c.syms["TreeMonSet_Route"]
    table = []
    for _ in range(2):  # common, then rare
        while r.c.pb.memory[bank, addr] != 0xFF:
            table.append((r.c.pb.memory[bank, addr + 2],
                          r.c.pb.memory[bank, addr + 1]))
            addr += 3
        addr += 1
    assert table, "no Route treemon entries were read"

    r.c.write("wMapGroup", ROUTE_29[0])
    r.c.write("wMapNumber", ROUTE_29[1])
    r.c.write("wTimeOfDay", TIME_DAY)

    def trees():
        out = set()
        for _ in range(200):
            r.c.write("wTempWildMonSpecies", 0)
            r.c.write("wCurPartyLevel", 0)
            r.call("TreeMonEncounter")
            sp = r.c.read("wTempWildMonSpecies")
            if sp:
                out.add((r.c.read("wCurPartyLevel"), sp))
        return out

    r.build(0x1234, mode=None)
    vanilla = trees()
    assert vanilla, "no headbutt encounters came back"
    assert vanilla <= set(table), f"{vanilla - set(table)} is not a Route tree slot"

    r.build(0x1234, MODE_UNTIERED)
    fwd = r.forward()
    shuffled = trees()
    assert shuffled, "no headbutt encounters came back with the shuffle on"
    allowed = {(lvl, fwd[sp]) for lvl, sp in table}
    assert shuffled <= allowed, \
        f"headbutt gave {shuffled - allowed}, not a mapped tree slot"
    assert shuffled != vanilla, "headbutt species were not shuffled at all"


@check
def area_screen_scans_the_vanilla_slots(r):
    # FindNest paints the map screen from the vanilla encounter tables, so
    # with the shuffle on it has to be asked about the species that now
    # turns into the one the player is looking at.
    PIDGEY = 16
    screen = 20 * 18

    def nest(species):
        r.c.write("wNamedObjectIndex", species)
        r.call("FindNest", E=0)  # 0 = Johto
        after = r.c.read("wNamedObjectIndex")
        assert after == species, \
            f"FindNest left wNamedObjectIndex at {after}, not {species}"
        return r.c.read_block("wTilemap", screen)

    r.build(0x1234, mode=None)
    vanilla = nest(PIDGEY)
    assert any(vanilla), "FindNest marked nothing for Pidgey"

    r.build(0x1234, MODE_TIERED)
    fwd = r.forward()
    assert nest(fwd[PIDGEY]) == vanilla, \
        "the AREA screen does not follow the shuffled species"
    # And asking about the vanilla species now finds a different map.
    assert nest(PIDGEY) != vanilla, \
        "the AREA screen ignored the shuffle"


@check
def save_and_reload_rebuilds_the_same_maps(r):
    # The maps are not saved, only wPlusSeed is, so a reload has to rebuild
    # them byte for byte or a loaded game would drift from a saved one.
    #
    # Keep this check last: it shuts the shared emulator down and boots a
    # second one from the battery save it just wrote.
    r.build(0xC0DE, MODE_TIERED)
    seed = r.c.read16("wPlusSeed")
    before = r.forward()
    r.call("SaveGameData")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r.c.pb.stop(save=True)
    written = os.path.join(root, "pokecrystal.gbc.ram")
    assert os.path.exists(written), "PyBoy did not write the battery save"
    tmp = os.path.join(tempfile.gettempdir(), "plus_test.sav")
    shutil.copy(written, tmp)
    os.remove(written)

    c2 = Crystal(sav=tmp)
    try:
        c2.continue_game()
        assert c2.read16("wPlusSeed") == seed, "wPlusSeed did not survive the save"
        assert c2.read("wPlusFlags") == flags(MODE_TIERED), \
            "wPlusFlags did not survive the save"
        after = list(c2.read_block("wPlusWildMap", NUM_POKEMON + 1))
        assert after == before, "the reloaded game rebuilt a different map"
    finally:
        c2.stop()
        os.remove(tmp)


def main():
    failures = []
    with Runner() as r:
        for fn in CHECKS:
            try:
                fn(r)
            except AssertionError as e:
                failures.append(f"{fn.__name__}: {e}")
                print(f"FAIL {fn.__name__}: {e}")
            else:
                print(f"ok   {fn.__name__}")
    print()
    if failures:
        print(f"{len(failures)} of {len(CHECKS)} checks failed")
        return 1
    print(f"all {len(CHECKS)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
