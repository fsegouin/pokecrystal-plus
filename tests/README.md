# Tests

PyBoy-driven checks for Pokémon Crystal+ features. Not part of `make`.

    python3 -m venv .venv && .venv/bin/pip install -r tests/requirements.txt
    make crystal
    .venv/bin/python tests/harness.py           # smoke test
    .venv/bin/python tests/test_wild.py         # wild encounter randomizer
    .venv/bin/python tests/test_trainer.py      # trainer roster randomizer
    .venv/bin/python tests/test_exp.py          # catch-up EXP booster
    .venv/bin/python tests/test_rematch.py      # trainer and gym leader rematches
    .venv/bin/python tests/test_fps.py          # 60 fps overworld option
    .venv/bin/python tests/test_running.py      # running shoes (hold B)
    .venv/bin/python tests/test_text.py         # INST text speed, start menu timing
    .venv/bin/python tests/test_hud.py          # one-line battle HUD
    .venv/bin/python tests/test_repel.py        # $1 repels, mart stock, top-off
    .venv/bin/python tests/test_fixes.py        # vanilla bug fixes, low HP alarm
    .venv/bin/python tests/test_matchups.py     # type matchup markers on the move list
    .venv/bin/python tests/test_battle_menu.py  # B on the battle menu moves to RUN
    .venv/bin/python tests/measure_overworld.py # overworld loop timings
    .venv/bin/python tests/compare_builds.py other.gbc

`make_chain_save.py` starts from `fps60.sav` and writes `chain0.sav` and
`chain39.sav` to `tests/states/`: standing in the Route 34 grass with a
healthy party, with no chain and one win from the top tier.
`give_radar.py <name>` (default `chain39`) puts the POKé RADAR into
`tests/states/<name>.sav` in place, going through the game's own
`SaveGameData`, since the key items pocket is inside the checksummed save
block and cannot be patched in the file.

`battle_now.py` drops you straight into a battle in a window, to look at the
HUD: `.venv/bin/python tests/battle_now.py`. It writes a party mon of its own,
because the saves ship with an empty party and a trainer battle that cannot
start leaves the approach script waiting on a movement forever.

`matchups_now.py` does the same for the type matchup markers: a wild
Normal/Flying type from the Route 34 grass against a lead knowing LICK,
THUNDERSHOCK, VINE WHIP and TACKLE, so FIGHT shows ×, ▲, ▼ and a blank. It
needs `chain0.sav`; `--check` opens FIGHT headless instead and reports what
it finds.

`tests/playtest.py` is a windowed play helper rather than a check; see below.
`dump_options_tilemap.py <file>` writes the options screen's background
tilemap to `<file>`, to diff between two builds.

Most of `test_wild.py` needs no save state. It boots the ROM, mashes through
the new game flow once, and from there calls the routines under test directly:
it parks the CPU in a two byte loop in HRAM, sets the registers and program
counter, and reads the result out of WRAM. That covers the map builder and the
vanilla encounter routines at their hook sites without walking to a route.
The few shiny and chain checks that need a party or a start menu to look at
are the exception: they load `tests/states/fps60.sav`.

## Hand-offs: battery saves and states

Many checks need the game at a particular point (in tall grass, facing a
trainer, mid-battle). Two ways to hand one over:

**Battery save (preferred).** Save in-game at the spot, in any emulator, and
drop the `.sav` in `tests/states/<name>.sav`. It is a raw SRAM dump, so it
loads into any build of the ROM: `Crystal(sav=...)` then `continue_game()`.

**Save state.** For mid-battle or mid-cutscene spots a battery save can't
capture: run the ROM in the PyBoy window, play to the spot, press **Z**,
close the window. That writes `pokecrystal.gbc.state`; move it to
`tests/states/<name>.state`. States embed CPU state, so they only load into
the exact build they came from.

    .venv/bin/python -m pyboy pokecrystal.gbc

Keys: arrows, A = a, B = s, Start = Enter, Select = Backspace, Space = turbo.
`tests/states/` is gitignored.

`Crystal.call(symbol, **regs)` runs one ROM routine with the registers set
explicitly, which is what a routine taking an argument in `a` needs.
`Crystal.farcall(symbol)` goes through the game's own `rst FarCall` vector, so
it owns `a` and `hl` and cannot pass either.

`Crystal.farcall(symbol)` runs one ROM routine on its own from a cold boot, so
a feature whose inputs and outputs are all memory can be checked without
reaching the situation that would normally call it. `test_exp.py` uses it.
`test_rematch.py` needs no emulator at all: it decodes the assembled script
bytecode out of the ROM using an opcode table parsed from
`macros/scripts/events.asm`.

`boot.py` scripts a brand-new game up to the overworld and caches the result
as a save state keyed by the ROM's hash, and `nav.py` walks from there to New
Bark Town. Between them, no check needs a hand-made save state.

## Handing over a position to test

Some checks need the game at a place a script cannot reach in reasonable time,
usually because it is gated behind a starter, badges or an HM. To hand one
over, play there and keep the battery save:

    .venv/bin/python tests/playtest.py gamecorner

That opens a window, resuming from `tests/states/gamecorner.sav` if it exists.
Play to the spot, save in game (START, SAVE, YES), then close the window. The
save lands in `tests/states/<name>.sav` and a check can load it with
`Crystal(sav="tests/states/gamecorner.sav")` followed by `continue_game()`.

Use a battery save rather than a PyBoy save state for this. A state embeds CPU
state and only loads into the exact ROM build it came from, so it breaks on the
next rebuild; a battery save does not.

Three saves are expected by name, and `tests/states/` is gitignored, so a fresh
clone has to make them once with `playtest.py`:

* `fps30.sav` and `fps60.sav`, the east-west stretch in Goldenrod with the
  60 fps option off and on, used by `test_running.py` and `test_text.py`;
  `test_hud.py`, `test_matchups.py`, `test_battle_menu.py`, `battle_now.py`
  and part of `test_wild.py` need `fps60.sav` alone;
* `gamecorner.sav`, in front of the Goldenrod prize vendor, used by
  `test_text.py`.

`make_chain_save.py` makes `chain0.sav` and `chain39.sav` from `fps60.sav`.
`test_repel.py` needs `chain0.sav`, since it walks real steps in the Route 34
grass, and so does `matchups_now.py`; `chain39.sav` is only for playing the
chain by hand.

A script whose save is missing reports it as a failure, not a skip.
