"""PyBoy harness for Pokémon Crystal+.

    from harness import Crystal
    c = Crystal()                    # boots pokecrystal.gbc headless
    c.load_state('route29')          # a state you saved with Z in the PyBoy window
    c.press('A'); c.run(60)
    c.read('wTempWildMonSpecies')    # by symbol, via pokecrystal.sym
    c.screenshot('out.png')

Buttons: A B START SELECT UP DOWN LEFT RIGHT.
"""
import io
import logging
import os
import re

# Scoped to the import: PyBoy logs while loading, but leaving the global
# disable in place would silence every other library in the process too.
logging.disable(logging.WARNING)
from pyboy import PyBoy  # noqa: E402
logging.disable(logging.NOTSET)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM = os.path.join(ROOT, "pokecrystal.gbc")
SYM = os.path.join(ROOT, "pokecrystal.sym")
STATES = os.path.join(ROOT, "tests", "states")

# MBC3 with a battery: four 8 KiB SRAM banks. PyBoy reads exactly this
# many bytes out of ram_file, so a blank battery has to be full length.
SRAM_SIZE = 4 * 8 * 1024

# pb.memory[bank, addr] is valid below $E000; OAM, I/O and HRAM above it must be
# indexed without a bank, and .sym reports them as bank 00.
BANKED_LIMIT = 0xE000


def load_symbols(path=SYM):
    """{name: (bank, addr)} from an rgblink .sym file."""
    syms = {}
    with open(path) as f:
        for line in f:
            m = re.match(r"([0-9a-f]{2}):([0-9a-f]{4}) (\S+)", line.strip(), re.I)
            if m:
                syms[m.group(3)] = (int(m.group(1), 16), int(m.group(2), 16))
    return syms


class Crystal:
    def __init__(self, rom=ROM, window="null", sav=None):
        """`sav`: path to a battery save (.sav / .ram, raw 32 KiB SRAM dump).
        Battery saves are ROM-independent, so prefer them over states for
        hand-offs; after boot, use continue_game() to load it."""
        self.syms = load_symbols(os.path.splitext(rom)[0] + ".sym")
        # Read into a buffer so the handle closes deterministically; PyBoy only
        # needs a file-like object.
        # Always hand PyBoy a buffer. With ram_file=None it derives a battery
        # file next to the ROM, so a stray pokecrystal.gbc.ram silently changes
        # where a "new game" starts.
        ram = io.BytesIO(bytes(SRAM_SIZE))
        if sav:
            with open(sav, "rb") as f:
                ram = io.BytesIO(f.read())
        self.pb = PyBoy(rom, window=window, cgb=True, log_level="ERROR", ram_file=ram)
        self.pb.set_emulation_speed(0)

    def continue_game(self):
        """From power-on with a battery save present: skip the intro and pick
        CONTINUE on the main menu. Returns once the overworld is loaded."""
        self.run(60)
        for _ in range(12):            # copyright / Game Freak / intro / title
            self.press("A"); self.run(30)
        self.press("A"); self.run(30)  # CONTINUE is the first menu entry
        self.press("A"); self.run(120) # confirm save info box

    def run(self, frames=1):
        # tick(n) renders only the last frame of the batch, which is all
        # screenshot() needs; per-frame ticking is much slower.
        if frames > 0:
            self.pb.tick(frames, render=True)

    def press(self, button, hold=4, release=4):
        b = button.lower()
        self.pb.button_press(b)
        self.run(hold)
        self.pb.button_release(b)
        self.run(release)

    def addr(self, name):
        return self.syms[name][1]

    def bank(self, name):
        return self.syms[name][0]

    def read(self, name, offset=0):
        """Read one byte at symbol+offset. ROM, SRAM and WRAMX symbols are read
        from the bank the .sym names, not whichever bank is currently paged in."""
        bank, a = self.syms[name]
        a += offset
        if a < BANKED_LIMIT:
            return self.pb.memory[bank, a]
        return self.pb.memory[a]

    def read16(self, name, offset=0):
        return self.read(name, offset) | (self.read(name, offset + 1) << 8)

    def write(self, name, value, offset=0):
        bank, a = self.syms[name]
        a += offset
        if a < 0x8000:
            # An unbanked write here is an MBC command, not a store.
            raise ValueError(f"{name} is in ROM at ${a:04x}; refusing to write")
        if a < BANKED_LIMIT:
            self.pb.memory[bank, a] = value
        else:
            self.pb.memory[a] = value

    def read_block(self, name, length):
        return bytes(self.read(name, i) for i in range(length))

    def load_state(self, name):
        p = name if os.path.exists(name) else os.path.join(STATES, name + ".state")
        with open(p, "rb") as f:
            self.pb.load_state(f)

    def save_state(self, name):
        os.makedirs(STATES, exist_ok=True)
        path = os.path.abspath(os.path.join(STATES, name + ".state"))
        if os.path.commonpath([STATES, path]) != STATES:
            raise ValueError(f"state name escapes {STATES}: {name!r}")
        with open(path, "wb") as f:
            self.pb.save_state(f)

    def screenshot(self, path):
        self.pb.screen.image.save(path)

    def stop(self):
        self.pb.stop(save=False)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()
        return False


if __name__ == "__main__":
    with Crystal() as c:
        c.run(900)
        print("wOptions =", hex(c.read("wOptions")))
