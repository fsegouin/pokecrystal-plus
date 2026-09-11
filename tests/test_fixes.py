"""Vanilla bug fixes and the four-beep low HP alarm (Crystal+).

Every fix is pret's own, from docs/bugs_and_glitches.md, and each site keeps
pret's title with "; BUG:" turned into "; plus: fixed:". The first group
checks that swap for every fix applied. The rest call the fixed routines
directly on a booted game, for the fixes whose inputs and outputs are all
memory: most of the battle engine ones only show mid-battle, and the existing
battle checks in test_hud.py and test_wild.py walk through that code.

Run: .venv/bin/python tests/test_fixes.py
"""
import glob
import os
import re
import sys

from harness import ROOT, Crystal

FIXED = [
    "Five-digit experience gain is printed incorrectly",
    "BRN/PSN/PAR do not affect catch rate",
    "HELD_CATCH_CHANCE has no effect",
    "Moon Ball does not boost catch rate",
    "Love Ball boosts catch rate for the wrong gender",
    "Fast Ball only boosts catch rate for three Pokémon",
    "SFX_RUN does not play correctly when a wild Pokémon flees from battle",
    "Perish Song and Spikes can leave a Pokemon with 0 HP and not faint",
    "Berserk Gene's confusion lasts for 256 turns or the previous Pokémon's confusion count",
    "A Pokémon that fainted from Pursuit will have its old status condition when revived",
    "A Disabled but PP Up–enhanced move may not trigger Struggle",
    "PRZ and BRN stat reductions don't apply to switched Pokémon",
    "Glacier Badge may not boost Special Defense depending on the value of Special Attack",
    "Moves with a 100% secondary effect chance will not trigger it in 1/256 uses",
    "Belly Drum sharply boosts Attack even with under 50% HP",
    "Return and Frustration deal no damage when the user's happiness is low or high, respectively",
    "Wild Pokémon can always Teleport regardless of level difference",
    "HP bar animation is slow for high HP",
    "HP bar animation off-by-one error for low HP",
    "AI might use its base reward value as an item",
    "AI use of Full Heal does not cure confusion status",
    "AI use of Full Heal or Full Restore does not cure Nightmare status",
    "AI use of Full Heal or Full Restore does not cure Attack or Speed drops from burn or paralysis",
    '"Smart" AI discourages Conversion2 after the first turn',
    '"Smart" AI encourages Mean Look if its own Pokémon is badly poisoned',
]


def constants(*names):
    """Every `const` in constants/, numbered the way const_def numbers them.
    Name files (without .asm) to read only those, where a name could clash."""
    values = {}
    paths = [os.path.join(ROOT, "constants", f"{n}.asm") for n in names] or \
        glob.glob(os.path.join(ROOT, "constants", "*.asm"))
    for path in paths:
        value, step = 0, 1
        for line in open(path, encoding="utf-8"):
            code = line.split(";")[0].strip()
            words = code.replace(",", " ").split()
            if not words:
                continue
            args = []
            for w in words[1:]:
                try:
                    args.append(int(w.replace("$", "0x"), 0))
                except ValueError:
                    break
            if words[0] == "const_def":
                value = args[0] if args else 0
                step = args[1] if len(args) > 1 else 1
            elif words[0] == "const" and len(words) == 2:
                values.setdefault(words[1], value)
                value += step
            elif words[0] == "const_skip":
                value += step * (args[0] if args else 1)
            elif words[0] == "const_next" and args:
                value = args[0]
    return values


C = constants()


class Checks:
    def __init__(self):
        self.failures = []

    def __call__(self, label, got, want):
        ok = got == want
        if not ok:
            self.failures.append(label)
        print(f"  {'ok  ' if ok else 'FAIL'} {label}: got {got!r}, want {want!r}")


def check_markers(check):
    print("every fix is marked as applied")
    sources = []
    for d in ("audio", "data", "engine", "home"):
        for path in glob.glob(os.path.join(ROOT, d, "**", "*.asm"), recursive=True):
            sources.append(open(path, encoding="utf-8").read())
    text = "\n".join(sources)
    for title in FIXED:
        left = f"; BUG: {title}" in text
        done = f"; plus: fixed: {title}" in text
        check(title[:60], (left, done), (False, True))


def stat(c, name):
    return c.read(name) << 8 | c.read(name, 1)


def set_stat(c, name, value):
    c.write(name, value >> 8)
    c.write(name, value & 0xFF, offset=1)


def check_routines(c, check):
    print("five-digit EXP")
    lo, hi = c.addr("wStringBuffer2") & 0xFF, c.addr("wStringBuffer2") >> 8
    for label in ("_ExpPointsText", "_BoostedExpPointsText"):
        bank, addr = c.syms[label]
        raw = bytes(c.pb.memory[bank, addr + i] for i in range(40))
        at = raw.find(bytes([lo, hi]))
        check(f"{label} prints two bytes as five digits", raw[at + 2] if at >= 0 else None, 0x25)

    print("Return and Frustration never hit for 0")
    c.write("hBattleTurn", 0)
    for happiness in (0, 1, 2, 3, 100, 255):
        c.write("wBattleMonHappiness", happiness)
        c.call("BattleCommand_HappinessPower")
        check(f"Return at happiness {happiness}", c.pb.register_file.D, max(1, happiness * 10 // 25))
    for happiness in (255, 254, 253, 252, 0):
        c.write("wBattleMonHappiness", happiness)
        c.call("BattleCommand_FrustrationPower")
        check(f"Frustration at happiness {happiness}", c.pb.register_file.D,
              max(1, (255 - happiness) * 10 // 25))

    print("Moon Ball and Fast Ball")
    for species, boosted in (("CLEFAIRY", True), ("NIDORINA", True), ("JIGGLYPUFF", True),
                             ("PIKACHU", False), ("RATTATA", False)):
        c.write("wTempEnemyMonSpecies", C[species])
        c.call("MoonBallMultiplier", b=10)
        check(f"Moon Ball on {species}", c.pb.register_file.B, 40 if boosted else 10)
    for species, boosted in (("MAGNEMITE", True), ("GRIMER", True), ("HERACROSS", True),
                             ("QUAGSIRE", True), ("ENTEI", True), ("PIDGEY", False)):
        c.write("wTempEnemyMonSpecies", C[species])
        c.call("FastBallMultiplier", b=10)
        check(f"Fast Ball on {species}", c.pb.register_file.B, 40 if boosted else 10)

    print("Glacier Badge boosts both special stats")
    c.write("wLinkMode", 0)
    c.write("wInBattleTowerBattle", 0)
    c.write("wJohtoBadges", 1 << C["GLACIERBADGE"])
    names = ["wBattleMonAttack", "wBattleMonDefense", "wBattleMonSpeed",
             "wBattleMonSpclAtk", "wBattleMonSpclDef"]
    for name in names:
        set_stat(c, name, 100)
    c.call("BadgeStatBoosts")
    check("stats after Glacier Badge alone", [stat(c, n) for n in names], [100, 100, 100, 112, 112])

    print("the low HP alarm beeps four times, then stops")
    c.write("wLowHealthAlarm", 0x80)
    seen = []
    for _ in range(150):
        c.call("PlayDanger")
        seen.append(c.read("wLowHealthAlarm"))
    check("still beeping after 119 frames", seen[118], 0xFD)
    check("parked after 120", seen[119], 0xFF)
    check("and stays parked", seen[149], 0xFF)
    check("four beeps counted", sorted({v >> 5 & 3 for v in seen[:119]}), [0, 1, 2, 3])

    c.write("wBattleMonHP", 0)
    c.write("wBattleMonHP", 16, offset=1)
    c.write("wBattleLowHealthAlarm", 0)
    c.write("wPlayerHPPal", C["HP_RED"] if "HP_RED" in C else 2)
    c.write("wLowHealthAlarm", 0xFF)
    c.call("CheckDanger")
    check("a red bar leaves a finished alarm quiet", c.read("wLowHealthAlarm"), 0xFF)
    c.write("wPlayerHPPal", 0)  # HP_GREEN
    c.call("CheckDanger")
    check("leaving red clears it", c.read("wLowHealthAlarm"), 0)
    c.write("wPlayerHPPal", 2)  # HP_RED
    c.call("CheckDanger")
    check("the next red bar starts over", c.read("wLowHealthAlarm"), 0x80)

    print("the AI's Full Heal cures everything")
    c.write("wCurOTMon", 0)
    c.write("wOTPartyMon1Status", 1 << C["PSN"])
    c.write("wEnemyMonStatus", 1 << C["PSN"])
    c.write("wEnemyConfuseCount", 3)
    for name in ("wEnemySubStatus1", "wEnemySubStatus3", "wEnemySubStatus5"):
        c.write(name, 0xFF)
    c.call("AI_HealStatus", frames=8)
    check("status", (c.read("wOTPartyMon1Status"), c.read("wEnemyMonStatus")), (0, 0))
    check("confusion", (c.read("wEnemyConfuseCount"), c.read("wEnemySubStatus3") >> C["SUBSTATUS_CONFUSED"] & 1),
          (0, 0))
    check("Nightmare", c.read("wEnemySubStatus1") >> C["SUBSTATUS_NIGHTMARE"] & 1, 0)
    check("toxic", c.read("wEnemySubStatus5") >> C["SUBSTATUS_TOXIC"] & 1, 0)


def main():
    check = Checks()
    check_markers(check)
    with Crystal() as c:
        c.run(600)  # boot far enough that the stack and ROM bank are live
        check_routines(c, check)

    print()
    if check.failures:
        print(f"{len(check.failures)} failure(s): {', '.join(check.failures)}")
        return 1
    print("all fix checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
