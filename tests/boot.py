"""Shared boot helper: script a brand-new game up to the overworld.

There are no pre-made save states in the repo, so every check that needs the
overworld starts from power-on and mashes A through the intro, the clock, the
Prof Oak speech and the name menus (all of which default to a usable choice).
That takes a few seconds of wall time, so the result is cached as a save state
keyed by the ROM's contents: states embed CPU state and are only valid for the
build they came from, hence the hash in the name.
"""
import hashlib
import os

from harness import Crystal, ROM, STATES


def rom_tag(rom=ROM):
    with open(rom, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:12]


def new_game(c, max_presses=90):
    """Power-on to the first overworld frame. Returns the number of A presses."""
    c.run(240)
    for i in range(max_presses):
        c.press("A", hold=8, release=8)
        c.run(50)
        if c.read("wMapGroup"):
            c.run(120)
            return i
    raise RuntimeError("never reached the overworld")


def overworld(cache=True, **kw):
    """A Crystal sitting in the player's bedroom, from cache when possible."""
    c = Crystal(**kw)
    if not cache:
        new_game(c)
        return c
    name = "bedroom-" + rom_tag(kw.get("rom", ROM))
    path = os.path.join(STATES, name + ".state")
    if os.path.exists(path):
        c.load_state(path)
        return c
    new_game(c)
    c.save_state(name)
    return c
