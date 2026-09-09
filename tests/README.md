# Tests

PyBoy-driven checks for Pokémon Crystal+ features. Not part of `make`.

    python3 -m venv .venv && .venv/bin/pip install -r tests/requirements.txt
    make crystal
    .venv/bin/python tests/harness.py           # smoke test
    .venv/bin/python tests/test_wild.py         # per-feature scripts (added per phase)

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
