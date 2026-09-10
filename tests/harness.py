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

    @property
    def trap(self):
        """Two bytes of HRAM to park a called routine's return address in.

        The nineteen bytes after hClockResetTrigger close out the section and
        nothing in the game touches them. hMathBuffer, the obvious-looking
        choice, is scratch that Multiply writes through, so a routine that does
        any arithmetic overwrites the very instruction it is due to return to.
        """
        return self.syms["hClockResetTrigger"][1] + 8

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

    def farcall(self, name, frames=2):
        """Run one ROM routine on its own, the way `farcall` in the game does.

        Sets up a: hl for the rst $08 vector, points the return address at two
        bytes of `jr -2` parked in HRAM, then lets the CPU run until it spins
        there. Interrupts are masked for the duration so no handler can touch
        the routine's inputs, and WRAM bank 1 is paged in so WRAMX symbols
        resolve the way they do in the overworld. Boot first: this needs the
        stack and the ROM bank register in a sane state."""
        bank, addr = self.syms[name]
        pb, rf = self.pb, self.pb.register_file
        trap = self.trap
        pb.memory[trap] = 0x18      # jr -2
        pb.memory[trap + 1] = 0xFE
        saved_ie = pb.memory[0xFFFF]
        pb.memory[0xFFFF] = 0       # mask every interrupt
        pb.memory[0xFF70] = 1       # SVBK: WRAM bank 1
        sp = rf.SP - 2
        pb.memory[sp] = trap & 0xFF
        pb.memory[sp + 1] = trap >> 8
        rf.SP = sp
        rf.A = bank
        rf.HL = addr
        rf.PC = 0x0008              # rst FarCall
        self.run(frames)
        pb.memory[0xFFFF] = saved_ie
        if rf.PC != trap:
            raise RuntimeError(
                f"{name} did not return within {frames} frames (PC=${rf.PC:04x})")

    def call(self, name, frames=4, **regs):
        """Run a ROM routine with the registers set explicitly.

        farcall() goes through the rst FarCall vector, which owns a and hl, so
        it cannot pass arguments in them. This pages the routine's bank in
        itself and sets whatever registers are named, which is what Predef and
        anything taking an argument in a need. Register names are the ones
        PyBoy exposes: a, f, b, c, d, e, hl, sp, pc. There is no h, l, bc or
        de, so pass a pair as hl."""
        bank, addr = self.syms[name]
        pb, rf = self.pb, self.pb.register_file
        trap = self.trap
        pb.memory[trap] = 0x18      # jr -2
        pb.memory[trap + 1] = 0xFE
        saved_ie = pb.memory[0xFFFF]
        pb.memory[0xFFFF] = 0       # mask every interrupt
        pb.memory[0xFF70] = 1       # SVBK: WRAM bank 1
        saved_bank = self.read("hROMBank")
        if bank:
            # rst Bankswitch writes both the MBC register and hROMBank, and
            # every routine that pages a bank in restores itself from hROMBank
            # afterwards. Setting only the register leaves the game convinced
            # it is somewhere else, and the first GetFarByte along the way
            # comes back with the wrong bank's data.
            pb.memory[0x2000] = bank
            self.write("hROMBank", bank)
        sp = rf.SP - 2
        pb.memory[sp] = trap & 0xFF
        pb.memory[sp + 1] = trap >> 8
        rf.SP = sp
        for name_, value in regs.items():
            setattr(rf, name_.upper(), value)
        rf.PC = addr
        self.run(frames)
        pb.memory[0xFFFF] = saved_ie
        # farcall gets this back from ReturnFarCall; paging the bank in by hand
        # means putting it back by hand, or the game runs on the wrong one.
        if bank:
            pb.memory[0x2000] = saved_bank
            self.write("hROMBank", saved_bank)
        if rf.PC != trap:
            raise RuntimeError(
                f"{name} did not return within {frames} frames (PC=${rf.PC:04x})")

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
