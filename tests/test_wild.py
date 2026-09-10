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

from harness import STATES, Crystal  # noqa: E402

NUM_POKEMON = 251
UNOWN = 201

# wPlusFlags
PLUS_WILD_ENABLED_F = 0
PLUS_WILD_MODE_SHIFT = 1
MODE_TIERED, MODE_UNTIERED, MODE_CHAOS = 0, 1, 2

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
        # The harness picks the parking spot and carries the reasoning for it.
        self.pad = self.c.trap
        pb.memory[self.pad] = 0x18
        pb.memory[self.pad + 1] = 0xFE
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
        pb.memory[sp] = self.pad & 0xFF
        pb.memory[sp + 1] = self.pad >> 8
        rf.SP = sp
        rf.PC = addr
        for _ in range(30):
            pb.tick(1, render=False)
            if rf.PC in (self.pad, self.pad + 1):
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


def is_shiny(b, c):
    """The four tests CheckShininess makes, on a DV pair."""
    return (b >> 4) & 0b0010 and (b & 0xF) == 10 and c == 0xAA


@check
def script_mons_get_better_shiny_odds(r):
    """A mon a script hands over is one you keep, so it gets extra rolls of its
    DVs. Shininess here is nothing but the DVs, so an extra chance at one is
    literally an extra roll, and the count is the only dial."""
    PLAIN = (0x12, 0x34)
    assert not is_shiny(*PLAIN)

    for _ in range(400):
        r.c.write("wPlusShinyRolls", 0)
        r.c.call("PlusBoostShinyDVs", b=PLAIN[0], c=PLAIN[1])
        rf = r.c.pb.register_file
        assert (rf.B, rf.C) == PLAIN, "no allowance, so the game's roll stands"

    # Sixteen rolls is one in 512. Over 4000 mons that averages about eight; a
    # band this wide only catches the rate being wrong, not the run being lucky.
    hits = 0
    rolls = 4000
    for _ in range(rolls):
        r.c.write("wPlusShinyRolls", 16)
        r.c.call("PlusBoostShinyDVs", b=PLAIN[0], c=PLAIN[1])
        rf = r.c.pb.register_file
        if is_shiny(rf.B, rf.C):
            hits += 1
    assert 1 <= hits <= 30, f"expected roughly 8 shiny in {rolls}, got {hits}"

    # The count is a dial and nothing else, so turning it up has to move the
    # rate with it. At 255 rolls a shiny lands about once in 32, which is often
    # enough to see what the routine actually returns.
    seen = set()
    for _ in range(4000):
        r.c.write("wPlusShinyRolls", 255)
        r.c.call("PlusBoostShinyDVs", b=PLAIN[0], c=PLAIN[1])
        rf = r.c.pb.register_file
        if is_shiny(rf.B, rf.C):
            seen.add((rf.B, rf.C))
    assert len(seen) > 1, \
        f"a re-rolled shiny should vary, got only {seen}"
    # Attack is the one DV a shiny has any choice in: four bits, of which the
    # second must be set, leaving eight values. Forcing a fixed pair would show
    # up here as a single one.
    assert len({b >> 4 for b, _ in seen}) > 1, \
        "every shiny came out with the same Attack DV"

    r.c.write("wPlusShinyRolls", 0)


# The curve in data terms: the shortest chain that earns each allowance.
# Mirrors PlusChainTiers in engine/plus/wild.asm.
CHAIN_TIERS = ((40, 32), (30, 16), (20, 8), (10, 4))
PLUS_CHAIN_MAGIC = 0xC5
WILDMON, TRAINER_BATTLE = 1, 2
WIN, LOSE, DRAW = 0, 1, 2
RATTATA, PIDGEY = 19, 16


def set_chain(r, species, count):
    r.call("PlusChainStore", D=species, E=count)


def get_chain(r):
    rf = r.call("PlusChainLoad")
    got = (rf.D, rf.E)
    r.call("CloseSRAM")
    return got


def end_battle(r, species, result=WIN, mode=WILDMON):
    """Run the hook that settles the chain as a battle ends."""
    r.c.write("wBattleMode", mode)
    r.c.write("wBattleResult", result)
    r.c.write("wTempWildMonSpecies", species)
    r.call("PlusUpdateChain")
    return get_chain(r)


@check
def a_chain_builds_on_repeats_and_breaks_on_a_new_species(r):
    """Beating the same species over and over is the chain. Beating a
    different one starts again on that one."""
    r.call("PlusChainReset")
    assert get_chain(r) == (0, 0), "a reset chain should read as empty"

    for want in range(1, 6):
        got = end_battle(r, RATTATA)
        assert got == (RATTATA, want), f"beating Rattata {want} times gave {got}"

    got = end_battle(r, PIDGEY)
    assert got == (PIDGEY, 1), f"a different species should restart at 1, got {got}"


@check
def only_a_defeat_moves_the_chain(r):
    """Fleeing, being fled from and whiting out all leave the count alone:
    nothing died, so nothing changed. A trainer's mon is not a wild encounter
    at all."""
    set_chain(r, RATTATA, 12)
    for result in (LOSE, DRAW):
        got = end_battle(r, RATTATA, result=result)
        assert got == (RATTATA, 12), f"result {result} moved the chain to {got}"
    got = end_battle(r, PIDGEY, result=DRAW)
    assert got == (RATTATA, 12), f"fleeing a new species broke the chain: {got}"
    got = end_battle(r, PIDGEY, mode=TRAINER_BATTLE)
    assert got == (RATTATA, 12), f"a trainer battle moved the chain: {got}"


@check
def the_chain_count_holds_at_the_top(r):
    """The count is one byte. It has to stop, not wrap round to zero and throw
    the chain away at its most valuable."""
    set_chain(r, RATTATA, 255)
    got = end_battle(r, RATTATA)
    assert got == (RATTATA, 255), f"the count wrapped: {got}"


@check
def the_chain_pays_out_on_the_curve(r):
    """Each tier starts exactly where the table says, and only for the species
    actually being chained."""
    def rolls_for(species, chain_species, count):
        set_chain(r, chain_species, count)
        return r.call("PlusChainRollsFor", B=species).A

    for floor, allowance in CHAIN_TIERS:
        assert rolls_for(RATTATA, RATTATA, floor) == allowance, \
            f"a chain of {floor} should earn {allowance} rolls"
        assert rolls_for(RATTATA, RATTATA, floor - 1) != allowance, \
            f"a chain of {floor - 1} should not yet earn {allowance} rolls"

    for count in (0, 1, 9):
        assert rolls_for(RATTATA, RATTATA, count) == 0, \
            f"a chain of {count} should earn nothing"

    seen = [rolls_for(RATTATA, RATTATA, n) for n in range(60)]
    assert seen == sorted(seen), f"the curve dips: {seen}"

    assert rolls_for(PIDGEY, RATTATA, 200) == 0, \
        "a chain on another species paid out"
    assert rolls_for(PIDGEY, 0, 200) == 0, "an empty chain paid out"


@check
def an_allowance_is_spent_once(r):
    """The allowance has to be consumed by the roll it pays for. Left set, it
    would follow on to whatever the game generated next: catch a mon while a
    gift is part-way through and it would inherit the gift's odds."""
    r.c.write("wPlusShinyRolls", 200)
    r.c.call("PlusBoostShinyDVs", b=0x12, c=0x34)
    assert r.c.read("wPlusShinyRolls") == 0, "the allowance survived the roll"

    # A second mon with no allowance of its own must get the plain roll back.
    for _ in range(200):
        r.c.call("PlusBoostShinyDVs", b=0x12, c=0x34)
        rf = r.c.pb.register_file
        assert (rf.B, rf.C) == (0x12, 0x34), "a spent allowance was reused"


@check
def a_gift_mon_comes_out_intact(r):
    """A mon added the way a gift adds it keeps the PP for its moves.

    TryAddMonToParty is where GivePoke ends up, and GeneratePartyMonStats
    inside it is what carries the shiny hook. Driving the whole chain rather
    than the hook alone is the point: the hook is reached by farcall, which
    loads hl itself, so a call site that fails to save hl goes wrong only
    from here. FillPP walks the moves through hl a few lines further on, so
    these four bytes are either the moves' own PP or four bytes of ROM.
    """
    CYNDAQUIL = 155
    MOVE_PP, MOVE_LENGTH = 5, 7
    with Crystal(sav=os.path.join(STATES, "fps60.sav")) as c:
        c.continue_game()
        for rolls in (0, 16):
            c.write("wPartyCount", 0)
            c.write("wPlusShinyRolls", rolls)
            c.write("wMonType", 0)  # PARTYMON
            c.write("wCurPartySpecies", CYNDAQUIL)
            c.write("wCurPartyLevel", 5)
            c.call("TryAddMonToParty", frames=20)

            at = f"with an allowance of {rolls}"
            assert c.read("wPartyCount") == 1, f"{at}: the mon was not added"
            moves = [c.read("wPartyMon1Moves", i) for i in range(4)]
            assert any(moves), f"{at}: the mon knows no moves"
            pp = [c.read("wPartyMon1PP", i) for i in range(4)]
            want = [0 if m == 0 else
                    c.read("Moves", (m - 1) * MOVE_LENGTH + MOVE_PP) for m in moves]
            assert pp == want, \
                f"{at}: moves {moves} carry PP {pp}, expected {want}"
        c.write("wPlusShinyRolls", 0)


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


def read_menu_box(c):
    """The eight rows of the start menu's description box, as text."""
    def dec(t):
        t &= 0xFF
        if 0x80 <= t <= 0x99:
            return chr(ord("A") + t - 0x80)
        if 0xA0 <= t <= 0xB9:
            return chr(ord("a") + t - 0xA0)
        if 0xF6 <= t <= 0xFF:
            return chr(ord("0") + t - 0xF6)
        return " "
    tm = c.pb.tilemap_background
    return ["".join(dec(tm[x, y]) for x in range(10)).rstrip()
            for y in range(10, 18)]


def sav_with_chain(species, count):
    """A battery save carrying a chain, written the way the battle hook would.

    Patching SRAM in the file rather than calling PlusChainStore keeps the
    emulator playable: a direct call parks the CPU and the game never resumes.
    """
    src = os.path.join(STATES, "fps60.sav")
    data = bytearray(open(src, "rb").read())
    c = Crystal()
    try:
        syms = c.syms
    finally:
        c.stop()
    for name, val in (("sPlusChainCheck", PLUS_CHAIN_MAGIC),
                      ("sPlusChainSpecies", species), ("sPlusChainCount", count)):
        bank, addr = syms[name]
        data[bank * 0x2000 + (addr - 0xA000)] = val
    path = os.path.join(tempfile.gettempdir(), "plus_chain_menu.sav")
    with open(path, "wb") as f:
        f.write(bytes(data))
    return path


@check
def the_start_menu_shows_a_running_chain(r):
    """The description box grows by two rows to carry the chain, and the item
    description keeps the rows it has always had. The game double-spaces those
    two lines, so there is nothing free inside the original box to borrow."""
    with Crystal(sav=os.path.join(STATES, "fps60.sav")) as c:
        c.continue_game()
        c.press("start", hold=10, release=10)
        c.run(90)
        plain = read_menu_box(c)
    assert plain[:3] == ["", "", ""], \
        f"with no chain the box should not have grown: {plain}"
    desc = [row for row in plain if row]
    assert len(desc) == 2, f"expected two description lines, got {desc}"

    path = sav_with_chain(RATTATA, 37)
    try:
        with Crystal(sav=path) as c:
            c.continue_game()
            c.press("start", hold=10, release=10)
            c.run(90)
            chained = read_menu_box(c)
    finally:
        os.remove(path)

    assert chained[1] == "RATTATA", f"row 11 should name the species: {chained}"
    assert chained[2] == "Chain 37", f"row 12 should count it: {chained}"
    # The description has to come through untouched, on the same rows.
    assert chained[4:] == plain[4:], \
        f"the item description moved or was overwritten: {chained[4:]} vs {plain[4:]}"


@check
def a_wild_roll_spends_what_the_chain_earned(r):
    """The whole wild path in one go: what the battle engine calls, under the
    state a battle presents it with. PlusRollWildDVs stands in for the two
    BattleRandom calls, so this is exactly what a wild or static encounter
    gets.

    The pieces are checked apart elsewhere; this is the wiring between them.
    """
    def rate(chain_species, count, encounter, trials=3000):
        set_chain(r, chain_species, count)
        r.c.write("wBattleMode", WILDMON)
        r.c.write("wTempWildMonSpecies", encounter)
        hits = 0
        for _ in range(trials):
            rf = r.call("PlusRollWildDVs")
            if is_shiny(rf.B, rf.C):
                hits += 1
        return hits

    # A chain of 40 buys 32 rolls, about one in 256. Over 3000 encounters that
    # averages near twelve; the band is wide enough that only a wrong rate
    # trips it, not an unlucky run.
    hits = rate(RATTATA, 40, RATTATA)
    assert 3 <= hits <= 35, f"a chain of 40 gave {hits} shiny in 3000, expected ~12"

    # The same chain is worth nothing to a different species, and no chain is
    # worth nothing to anyone: both fall back to the roll the game makes.
    for label, chain_sp, count, enc in (("another species", RATTATA, 40, PIDGEY),
                                        ("no chain", 0, 0, RATTATA),
                                        ("below the first tier", RATTATA, 9, RATTATA)):
        hits = rate(chain_sp, count, enc, trials=2000)
        assert hits <= 3, f"{label} paid out: {hits} shiny in 2000"

    r.c.write("wBattleMode", 0)


@check
def a_chain_survives_a_reset_without_saving(r):
    """The whole reason the chain sits in SRAM rather than in the saved game
    block: it is written as the battle ends, not when the player saves. Beat a
    one-off encounter, reset without saving, and the world rolls back to the
    last save while the chain keeps the increment. That is what makes a static
    encounter chainable at all.

    Runs on its own emulator so the shared one is left alone.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    written = os.path.join(root, "pokecrystal.gbc.ram")
    tmp = os.path.join(tempfile.gettempdir(), "plus_chain.sav")

    c = Crystal()
    try:
        c.run(600)
        # No save is taken anywhere in here: the battle hook is the only thing
        # that writes, exactly as it would after beating a legendary.
        c.write("wBattleMode", WILDMON)
        c.write("wBattleResult", WIN)
        c.write("wTempWildMonSpecies", RATTATA)
        for _ in range(3):
            c.call("PlusUpdateChain")
    finally:
        c.pb.stop(save=True)
    assert os.path.exists(written), "PyBoy did not write the battery save"
    shutil.copy(written, tmp)
    os.remove(written)

    c2 = Crystal(sav=tmp)
    try:
        c2.run(600)
        c2.call("PlusChainLoad")
        rf = c2.pb.register_file
        got = (rf.D, rf.E)
        c2.call("CloseSRAM")
        assert got == (RATTATA, 3), f"the chain did not survive the reset: {got}"
    finally:
        c2.stop()
        os.remove(tmp)


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
