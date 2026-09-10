"""Trainer and gym leader rematches (Crystal+ phase 4).

Reads the assembled script bytecode straight out of pokecrystal.gbc and
decodes it with an opcode table parsed from macros/scripts/events.asm, then
asserts the shape of every rematch branch: that it offers the battle, that it
reaches startbattle, and, for the gym leaders, that it awards no badge and
gives no TM.

This is a static check on purpose. Reaching a beaten trainer in a running game
needs a party, a badge or two and a defeated opponent, none of which exist
without a save file, and tests/states/ ships empty. See the note at the bottom
of this file for the two save states that would let the dynamic checks run.

Run: .venv/bin/python tests/test_rematch.py
"""
import os
import re
import sys

from harness import ROOT, load_symbols

EVENTS = os.path.join(ROOT, "macros", "scripts", "events.asm")
ROM = os.path.join(ROOT, "pokecrystal.gbc")

# Commands that end a straight-line run of script bytes.
TERMINATORS = {"end", "endall", "sjump", "farsjump", "memjump", "jumpstd",
               "jumptext", "farjumptext", "jumptextfaceplayer", "jumpopenedtext",
               "warp", "halloffame", "returnafterbattle"}

# Nothing on a rematch path may award progression.
FORBIDDEN = {"setflag", "giveitem", "verbosegiveitem", "giveitemfrompc",
             "itemnotify", "setevent"}


def opcode_table():
    """{opcode: (name, operand length)} from the script command macros."""
    src = open(EVENTS).read()
    opcodes = {}
    for name, num in re.findall(r"^\tconst (\w+)_command ; \$([0-9a-fA-F]{2})",
                                src, re.M):
        opcodes[int(num, 16)] = name
    table = {}
    for num, name in opcodes.items():
        body = re.search(r"^MACRO " + name + r"$(.*?)^ENDM$", src, re.M | re.S)
        if not body:
            table[num] = (name, None)
            continue
        size = 0
        for line in body.group(1).splitlines():
            line = line.split(";")[0].strip()
            m = re.match(r"^(db|dw|dba|dbw|dl)\s+(.*)$", line)
            if not m:
                continue
            per = {"db": 1, "dw": 2, "dba": 3, "dbw": 3, "dl": 4}[m.group(1)]
            args = [a for a in m.group(2).split(",") if a.strip()]
            size += per * max(1, len(args))
        # The leading `db <name>_command` is the opcode itself.
        table[num] = (name, size - 1 if size else None)
    return table


class Rom:
    def __init__(self):
        self.data = open(ROM, "rb").read()
        self.syms = load_symbols()
        # Every symbol address in a bank, so a label's region can be bounded.
        self.bounds = {}
        for bank, addr in self.syms.values():
            self.bounds.setdefault(bank, set()).add(addr)
        self.names = {}
        for name, (bank, addr) in self.syms.items():
            self.names.setdefault((bank, addr), name)

    def offset(self, bank, addr):
        return bank * 0x4000 + (addr - 0x4000 if addr >= 0x4000 else addr)

    def label(self, bank, addr):
        return self.names.get((bank, addr))


def decode(rom, table, symbol, limit=64):
    """[(name, operand bytes, address)] from `symbol` to its terminator."""
    bank, addr = rom.syms[symbol]
    later = sorted(a for a in rom.bounds[bank] if a > addr)
    stop = later[0] if later else 0x8000
    out = []
    while addr < stop and len(out) < limit:
        op = rom.data[rom.offset(bank, addr)]
        if op not in table:
            raise AssertionError(f"{symbol}: unknown opcode ${op:02x} at ${addr:04x}")
        name, size = table[op]
        if size is None:
            raise AssertionError(f"{symbol}: {name} has no fixed size, cannot decode")
        start = rom.offset(bank, addr) + 1
        out.append((name, rom.data[start:start + size], addr))
        addr += 1 + size
        if name in TERMINATORS:
            break
    return out


def word(b, i=0):
    return b[i] | (b[i + 1] << 8)


GYMS = [
    ("VioletGymFalknerScript.Rematch", "FalknerWinLossText"),
    ("AzaleaGymBugsyScript.Rematch", "BugsyText_ResearchIncomplete"),
    ("GoldenrodGymWhitneyScript.Rematch", "WhitneyShouldntBeSoSeriousText"),
    ("EcruteakGymMortyScript.Rematch", "MortyWinLossText"),
    ("CianwoodGymChuckScript.Rematch", "ChuckLossText"),
    ("OlivineGymJasmineScript.Rematch", "Jasmine_BetterTrainer"),
    ("MahoganyGymPryceScript.Rematch", "PryceText_Impressed"),
    ("BlackthornGymClairScript.StartRematch", "ClairWinText"),
    ("PewterGymBrockScript.Rematch", "BrockWinLossText"),
    ("CeruleanGymMistyScript.Rematch", "MistyWinLossText"),
    ("VermilionGymSurgeScript.Rematch", "LtSurgeWinLossText"),
    ("CeladonGymErikaScript.Rematch", "ErikaBeatenText"),
    ("FuchsiaGymJanineScript.Rematch", "JanineText_ToughOne"),
    ("SaffronGymSabrinaScript.Rematch", "SabrinaWinLossText"),
    ("SeafoamGymBlaineScript.Rematch", "BlaineWinLossText"),
    ("ViridianGymBlueScript.Rematch", "LeaderBlueWinText"),
]

# Clair's two offers share BlackthornGymClairScript.StartRematch.
OFFERS = ["BlackthornGymClairScript.Rematch",
          "BlackthornGymClairScript.RematchAfterTM"]


def main():
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(label)
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}"
              f"{'' if got == want else f': got {got!r}, want {want!r}'}")

    table = opcode_table()
    rom = Rom()
    offer_bank, offer_addr = rom.syms["RematchOfferText"]

    print("map trainers")
    talk = decode(rom, table, "TalkToTrainerScript")
    names = [n for n, _, _ in talk]
    check("TalkToTrainerScript shape", names[:4],
          ["faceplayer", "trainerflagaction", "iftrue", "loadtemptrainer"])
    target = word(talk[2][1])
    check("beaten check branches to OfferRematchScript",
          rom.label(rom.syms["TalkToTrainerScript"][0], target),
          "OfferRematchScript")

    offer = decode(rom, table, "OfferRematchScript")
    names = [n for n, _, _ in offer]
    check("OfferRematchScript shape", names,
          ["opentext", "writetext", "yesorno", "iffalse", "closetext",
           "loadtemptrainer", "encountermusic", "sjump"])
    check("offers the shared text", word(offer[1][1]), offer_addr)
    check("yes goes to StartBattleWithMapTrainerScript",
          rom.label(offer_bank, word(offer[7][1])),
          "StartBattleWithMapTrainerScript")
    decline = rom.label(offer_bank, word(offer[3][1]))
    check("no goes to the decline branch", decline, "OfferRematchScript.decline")
    declined = decode(rom, table, "OfferRematchScript.decline")
    check("decline shape", [n for n, _, _ in declined], ["closetext", "sjump"])
    check("decline falls back to the vanilla after-battle script",
          rom.label(offer_bank, word(declined[1][1])), "AlreadyBeatenTrainerScript")

    beaten = decode(rom, table, "AlreadyBeatenTrainerScript")
    check("AlreadyBeatenTrainerScript still just talks",
          [n for n, _, _ in beaten], ["scripttalkafter"])

    print("gym leaders")
    for symbol, winloss in GYMS:
        gym = symbol.split("Script.")[0]
        body = decode(rom, table, symbol)
        names = [n for n, _, _ in body]
        bank = rom.syms[symbol][0]
        check(f"{gym}: battles and stops", names[-6:],
              ["closetext", "winlosstext", "loadtrainer", "startbattle",
               "reloadmapafterbattle", "end"])
        wl = next(b for n, b, _ in body if n == "winlosstext")
        check(f"{gym}: keeps the vanilla win text",
              rom.label(bank, word(wl)), winloss)
        forbidden = sorted(set(names) & FORBIDDEN)
        check(f"{gym}: no badge, no TM, no events", forbidden, [])
        if symbol not in ("BlackthornGymClairScript.StartRematch",):
            check(f"{gym}: asks first", "yesorno" in names, True)
            offers = [b for n, b, _ in body if n == "farwritetext"]
            check(f"{gym}: uses the shared offer text",
                  [(b[0], word(b, 1)) for b in offers],
                  [(offer_bank, offer_addr)])

    for symbol in OFFERS:
        body = decode(rom, table, symbol)
        names = [n for n, _, _ in body]
        bank = rom.syms[symbol][0]
        check(f"{symbol}: asks then shares the battle", names,
              ["farwritetext", "yesorno", "iftrue", "sjump"])
        check(f"{symbol}: yes reaches the shared battle",
              rom.label(bank, word(body[2][1])),
              "BlackthornGymClairScript.StartRematch")
        offer = body[0][1]
        check(f"{symbol}: uses the shared offer text",
              (offer[0], word(offer, 1)), (offer_bank, offer_addr))

    print()
    if failures:
        print(f"{len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print(f"all rematch checks passed ({len(GYMS)} gyms)")
    return 0


# Not covered here, and what it would take:
#
#   tests/states/beaten_trainer.sav - a battery save standing next to a map
#   trainer whose EVENT_BEAT_* flag is set, with a healthy party. Talk, answer
#   YES, and assert wBattleMode becomes 2 (trainer battle).
#
#   tests/states/beaten_gym.sav - a battery save inside a cleared gym, in front
#   of the leader, with a party that can win. Record VAR_BADGES and the TM
#   pocket, rematch, win, and assert both are unchanged.
#
# Both are reachable only by playing the game to that point; nothing in WRAM
# can be poked to fabricate a beaten trainer plus a viable party from a cold
# boot in reasonable time.

if __name__ == "__main__":
    sys.exit(main())
