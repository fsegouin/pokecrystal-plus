"""Checks for the Crystal+ trainer roster randomizer.

There is no save state in the repo and walking a fresh game as far as the
first trainer takes minutes of scripted input, so these boot to the main menu
and then run the battle-setup routine directly: point wOtherTrainerClass and
wOtherTrainerID at a trainer, then jump the CPU into ReadTrainerParty through
the game's own FarCall vector at $0008. That is the entry point a real battle
uses, so the hook, TryAddMonToParty and the level-up movesets all run for
real; only the walk to the trainer is skipped.

The return address pushed for the call is $0000, whose rst vector is
`di / jp Start`. A PyBoy hook there fires the moment the routine returns, the
party is read inside that hook, and the reset that follows is harmless because
the next check reloads the base state anyway.

    .venv/bin/python tests/test_trainer.py
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Crystal  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# trainer class ids, counted off the trainerclass entries in
# constants/trainer_constants.asm
FALKNER = 1
YOUNGSTER = 22
COOLTRAINERM = 27
COOLTRAINERF = 28

# vanilla rosters, from data/trainers/parties.asm
MIKEY = (YOUNGSTER, 2)          # db 2, PIDGEY / db 4, RATTATA
AARON = (COOLTRAINERM, 2)       # db 24, IVYSAUR / CHARMELEON / WARTORTLE
PAUL = (COOLTRAINERM, 3)        # db 34, DRATINI x3
QUINN = (COOLTRAINERF, 14)      # db 38, IVYSAUR / db 38, STARMIE
FALKNER1 = (FALKNER, 1)         # TRAINERTYPE_MOVES: 7 PIDGEY / 9 PIDGEOTTO

PLUS_TRAINERS_F = 3

# --- the ROM's own data, as the oracle -------------------------------------

def _species_table():
    order = []
    with open(os.path.join(ROOT, "data/pokemon/base_stats.asm")) as f:
        for line in f:
            m = re.search(r'INCLUDE "data/pokemon/base_stats/([a-z0-9_]+)\.asm"', line)
            if m:
                order.append(m.group(1))
    numbers = {}
    for i, stem in enumerate(order, 1):
        with open(os.path.join(ROOT, "data/pokemon/base_stats", stem + ".asm")) as f:
            const = re.search(r"db\s+([A-Z0-9_]+)\s*;\s*\d+", f.read()).group(1)
        numbers[const] = i
    return numbers


NUMBER = _species_table()
NAME = {v: k for k, v in NUMBER.items()}


def _evolutions():
    with open(os.path.join(ROOT, "data/pokemon/evos_attacks.asm")) as f:
        text = f.read()
    blocks = re.findall(r"^([A-Za-z0-9_]+)EvosAttacks:\n((?:\t.*\n|\n)*)", text, re.M)
    table = {}
    for i, (_, body) in enumerate(blocks, 1):
        entries = []
        for line in body.strip().split("\n"):
            line = line.strip()
            if not line.startswith("db"):
                continue
            args = [a.strip() for a in line[2:].split(";")[0].split(",")]
            if args[0] == "0":
                break
            entries.append(args)
        table[i] = entries
    return table


EVOLUTIONS = _evolutions()


def _bands():
    with open(os.path.join(ROOT, "data/plus/trainer_basics.asm")) as f:
        lines = f.read().split("\n")
    bands = {}
    current = None
    for line in lines:
        label = re.match(r"^PlusTrainerBasics(Late|Mid|Early):", line)
        if label:
            current = label.group(1).lower()
            bands[current] = []
            continue
        entry = re.match(r"^\tdb ([A-Z0-9_]+)", line)
        if entry and current:
            bands[current].append(NUMBER[entry.group(1)])
    return bands


BANDS = _bands()
BABIES = {NUMBER[n] for n in ("PICHU", "CLEFFA", "IGGLYBUFF", "TOGEPI")}


def _evo_levels():
    """Read the thresholds out of the asm so this oracle cannot drift from it."""
    path = os.path.join(ROOT, "constants/plus_constants.asm")
    src = open(path, encoding="utf-8").read()
    def const(name):
        m = re.search(rf"DEF {name}\s+EQU\s+(\d+)", src)
        assert m, f"{name} not found in constants/plus_constants.asm"
        return int(m.group(1))
    return const("PLUS_EVO_BABY_LEVEL"), const("PLUS_EVO_ITEM_LEVEL")


BABY_LEVEL, ITEM_LEVEL = _evo_levels()


def effective_level(level):
    return level - (level // 8 if level >= 30 else level // 4)


def _threshold(species, entry):
    method = entry[0]
    if method in ("EVOLVE_LEVEL", "EVOLVE_STAT"):
        return int(entry[1])
    if method == "EVOLVE_HAPPINESS":
        return BABY_LEVEL if species in BABIES else ITEM_LEVEL
    return ITEM_LEVEL  # EVOLVE_ITEM, EVOLVE_TRADE


def _outcomes(species, eff):
    applies = [e for e in EVOLUTIONS[species] if _threshold(species, e) <= eff]
    if not applies:
        return {species}
    reached = set()
    for entry in applies:
        reached |= _outcomes(NUMBER[entry[-1]], eff)
    return reached


def allowed_species(level):
    """Every species the randomizer may hand a trainer at this level."""
    pool = list(BANDS["early"])
    if level >= 15:
        pool += BANDS["mid"]
    if level >= 30:
        pool += BANDS["late"]
    eff = effective_level(level)
    reached = set()
    for basic in pool:
        reached |= _outcomes(basic, eff)
    return reached


# --- driving the ROM --------------------------------------------------------

class TrainerBattle:
    MAX_FRAMES = 120

    def __init__(self):
        self.c = Crystal()
        # Past the copyright and intro to the main menu, which sits idle. The
        # title screen would time out into the demo battle and call
        # ReadTrainerParty on its own.
        self.c.run(400)
        for _ in range(2):
            self.c.press("a")
            self.c.run(60)
        self.c.press("start")
        self.c.run(60)
        self.c.press("a")
        self.c.run(60)
        self.base = io.BytesIO()
        self.c.pb.save_state(self.base)
        self.stride = (self.c.syms["wOTPartyMon2Species"][1]
                       - self.c.syms["wOTPartyMon1Species"][1])
        self.captured = {}
        self.c.pb.hook_register(0, 0x0000, self._capture, self.captured)

    def _capture(self, captured):
        if captured:
            return
        count = self.c.read("wOTPartyCount")
        captured["party"] = [
            (self.c.read("wOTPartyMon1Species", i * self.stride),
             self.c.read("wOTPartyMon1Level", i * self.stride),
             tuple(self.c.read("wOTPartyMon1Moves", i * self.stride + m)
                   for m in range(4)))
            for i in range(min(count, 6))
        ]

    def party(self, trainer, flags=0, warmup=0):
        """`warmup` idles that many frames before the call. Reloading the same
        state rewinds the divider register that Random feeds on, so without it
        every run would replay the same rolls; a real battle is never reached
        on the same frame twice."""
        self.base.seek(0)
        self.c.pb.load_state(self.base)
        self.captured.clear()
        self.c.run(warmup)

        self.c.write("wLinkMode", 0)
        self.c.write("wInBattleTowerBattle", 0)
        self.c.write("wPlusFlags", flags)
        self.c.write("wOtherTrainerClass", trainer[0])
        self.c.write("wOtherTrainerID", trainer[1])

        pb = self.c.pb
        bank, addr = self.c.syms["ReadTrainerParty"]
        sp = pb.register_file.SP
        pb.memory[(sp - 1) & 0xFFFF] = 0x00
        pb.memory[(sp - 2) & 0xFFFF] = 0x00
        pb.register_file.SP = (sp - 2) & 0xFFFF
        pb.register_file.A = bank
        pb.register_file.HL = addr
        pb.register_file.PC = 0x0008

        for _ in range(self.MAX_FRAMES):
            pb.tick(1, False)
            if self.captured:
                return self.captured["party"]
        raise AssertionError("ReadTrainerParty never returned")

    def stop(self):
        self.c.stop()


def show(party):
    return [(NAME.get(s, s), lv) for s, lv, _ in party]


# --- the checks -------------------------------------------------------------

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}: {detail}")
        FAILURES.append(name)


def main():
    battle = TrainerBattle()
    on = 1 << PLUS_TRAINERS_F
    try:
        print("disabled behaves exactly like vanilla")
        mikey = battle.party(MIKEY)
        check("Mikey", show(mikey) == [("PIDGEY", 2), ("RATTATA", 4)], show(mikey))
        paul = battle.party(PAUL)
        check("Paul", show(paul) == [("DRATINI", 34)] * 3, show(paul))
        quinn = battle.party(QUINN)
        check("Quinn", show(quinn) == [("IVYSAUR", 38), ("STARMIE", 38)], show(quinn))
        aaron = battle.party(AARON)
        check("Aaron",
              show(aaron) == [("IVYSAUR", 24), ("CHARMELEON", 24), ("WARTORTLE", 24)],
              show(aaron))

        print("a TRAINERTYPE_MOVES trainer is untouched")
        falkner_off = battle.party(FALKNER1)
        check("Falkner vanilla",
              show(falkner_off) == [("PIDGEY", 7), ("PIDGEOTTO", 9)], show(falkner_off))
        same = all(battle.party(FALKNER1, on, warmup=i) == falkner_off
                   for i in range(1, 6))
        check("Falkner unchanged when enabled", same, show(battle.party(FALKNER1, on)))

        print("enabled: levels hold, species stay inside the pool")
        teams = []
        for trainer, vanilla in ((MIKEY, [2, 4]), (AARON, [24] * 3), (PAUL, [34] * 3),
                                 (QUINN, [38, 38])):
            bad_level = []
            bad_species = []
            seen = set()
            for i in range(20):
                party = battle.party(trainer, on, warmup=i)
                if [lv for _, lv, _ in party] != vanilla:
                    bad_level.append(show(party))
                for species, level, _ in party:
                    if species not in allowed_species(level):
                        bad_species.append((NAME.get(species, species), level))
                seen.add(tuple(s for s, _, _ in party))
            teams.append((trainer, seen))
            check(f"class {trainer[0]} id {trainer[1]}: levels unchanged",
                  not bad_level, bad_level[:3])
            check(f"class {trainer[0]} id {trainer[1]}: species in pool",
                  not bad_species, bad_species[:5])

        print("the roll is unseeded, so teams vary between battles")
        for trainer, seen in teams:
            check(f"class {trainer[0]} id {trainer[1]}: {len(seen)} distinct teams in 20",
                  len(seen) > 1, sorted(seen)[:3])

        print("a low-level trainer never draws from the higher bands")
        late_only = set(BANDS["late"]) - set(BANDS["mid"]) - set(BANDS["early"])
        drawn = set()
        for i in range(20):
            drawn |= {s for s, _, _ in battle.party(MIKEY, on, warmup=i)}
        check("Mikey draws early band only",
              not (drawn & late_only),
              sorted(NAME[s] for s in drawn & late_only))
    finally:
        battle.stop()

    if FAILURES:
        print(f"\n{len(FAILURES)} failed: {FAILURES}")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
