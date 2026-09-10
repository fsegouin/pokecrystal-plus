"""Catch-up EXP booster (Crystal+ phase 3).

Drives PlusCatchUpExpBoost directly with Crystal.farcall: the routine reads
wPlusFlags, wEnemyMonLevel and the recipient's MON_LEVEL and rewrites the
16-bit gain in hProduct + 2, so every input and output is a memory location a
test can set and read. That covers the arithmetic exactly, which reaching a
real KO in a wild battle would not: the EXP a battle hands over depends on
base exp, level, participant count and the three vanilla 1.5x paths, none of
which this feature is responsible for.

Run: .venv/bin/python tests/test_exp.py
"""
import sys

from harness import Crystal

PLUS_EXP_BOOST_F = 4


def boost_once(v):
    """One 1.5x step, saturating: what the assembly does to hProduct + 2."""
    return min(0xFFFF, v + (v >> 1))


def expected(gain, gap):
    """1.5 raised to (1 + gap // 3) when gap >= 1, else no change."""
    if gap < 1:
        return gain
    while gap >= 0:
        gain = boost_once(gain)
        gap -= 3
    return gain


def run_boost(c, gain, enemy_level, recipient_level, enabled=True):
    c.write("wPlusFlags", (1 << PLUS_EXP_BOOST_F) if enabled else 0)
    c.write("wCurPartyMon", 0)
    c.write("wPartyMon1Level", recipient_level)
    c.write("wEnemyMonLevel", enemy_level)
    c.write("hProduct", (gain >> 8) & 0xFF, offset=2)
    c.write("hProduct", gain & 0xFF, offset=3)
    c.farcall("PlusCatchUpExpBoost")
    return (c.read("hProduct", 2) << 8) | c.read("hProduct", 3)


def main():
    failures = []

    def check(label, got, want):
        ok = got == want
        if not ok:
            failures.append(label)
        print(f"  {'ok  ' if ok else 'FAIL'} {label}: got {got}, want {want}")

    with Crystal() as c:
        c.run(600)  # boot far enough that the stack and ROM bank are live

        print("multipliers at a fixed 1000 EXP gain")
        for gap in (0, 1, 2, 3, 4, 5, 6, 8, 9, 11, 12, 14, 15):
            recipient = 20
            enemy = recipient + gap
            got = run_boost(c, 1000, enemy, recipient)
            want = expected(1000, gap)
            check(f"gap {gap:2d} (x{got / 1000:.4g})", got, want)

        print("no boost when the recipient is not behind")
        check("recipient above the enemy", run_boost(c, 1000, 10, 30), 1000)
        check("recipient level equal", run_boost(c, 1000, 30, 30), 1000)

        print("no boost when the flag is clear")
        check("flag off, gap 12", run_boost(c, 1000, 40, 28, enabled=False), 1000)

        print("overflow clamp")
        # The worst vanilla case: Chansey's 255 base exp at level 100 over 7 is
        # 3642, then traded, trainer battle and Lucky Egg each add 1.5x.
        vanilla_max = 3642
        for _ in range(3):
            vanilla_max = boost_once(vanilla_max)
        check("vanilla stack alone stays 16-bit", vanilla_max < 0x10000, True)
        check("level 2 vs level 100, huge gain", run_boost(c, vanilla_max, 100, 2), 0xFFFF)
        check("already at the cap", run_boost(c, 0xFFFF, 100, 2), 0xFFFF)
        check("one step below the cap", run_boost(c, 0xFFFE, 21, 20), 0xFFFF)

        print("the recipient's own level is used, not the active battler's")
        c.write("wPartyMon1Level", 5)
        c.write("wPlusFlags", 1 << PLUS_EXP_BOOST_F)
        c.write("wCurPartyMon", 0)
        c.write("wEnemyMonLevel", 20)
        c.write("hProduct", 0, offset=2)
        c.write("hProduct", 100, offset=3)
        c.farcall("PlusCatchUpExpBoost")
        first = (c.read("hProduct", 2) << 8) | c.read("hProduct", 3)
        check("level 5 recipient, gap 15", first, expected(100, 15))
        # Same enemy, a second recipient that is not behind: untouched.
        c.write("wPartyMon1Level", 25)
        c.write("hProduct", 0, offset=2)
        c.write("hProduct", 100, offset=3)
        c.farcall("PlusCatchUpExpBoost")
        second = (c.read("hProduct", 2) << 8) | c.read("hProduct", 3)
        check("level 25 recipient, same enemy", second, 100)

        print("Celadon Cafe toggle")
        c.write("wPlusFlags", 0)
        c.farcall("PlusCheckExpBoost")
        check("reads off as off", c.read("wScriptVar"), 0)
        c.farcall("PlusToggleExpBoost")
        check("toggle turns it on", c.read("wScriptVar"), 1)
        check("only the boost bit moved", c.read("wPlusFlags"),
              1 << PLUS_EXP_BOOST_F)
        c.farcall("PlusCheckExpBoost")
        check("reads on as on", c.read("wScriptVar"), 1)
        c.write("wPlusFlags", 0xFF)
        c.farcall("PlusToggleExpBoost")
        check("toggle turns it off", c.read("wScriptVar"), 0)
        check("the other flags survive", c.read("wPlusFlags"),
              0xFF & ~(1 << PLUS_EXP_BOOST_F))

    print()
    if failures:
        print(f"{len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print("all EXP booster checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
