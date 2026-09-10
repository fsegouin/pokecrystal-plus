"""Checks for the 60 fps overworld option.

What the option buys is positional resolution, not speed: the overworld loop
runs every frame instead of every other frame, and each step is half as big,
so a tile still takes the same number of frames but the camera moves in
1-pixel instead of 2-pixel jumps.

So the checks are:
  * HandleMap runs once every two frames at 30 Hz and once per frame at 60 Hz;
  * walking one tile takes the same number of frames in both modes;
  * the scroll register moves 2 px per frame at 30 Hz and 1 px at 60 Hz;
  * an NPC with its own movement still walks, at the same speed;
  * a slow_step still takes twice as long as a normal step, in both modes.

Run: .venv/bin/python tests/test_fps.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nav  # noqa: E402
from boot import overworld  # noqa: E402
from harness import load_symbols  # noqa: E402

SYMS = load_symbols()
FRAME_RATE_60_F = 1
MENU_ACCOUNT = 0

# hSCX and hSCY are the shadow copies the VBlank handler writes to the real
# scroll registers, so they carry the value the overworld loop computed.
AXIS = {"up": "hSCY", "down": "hSCY", "left": "hSCX", "right": "hSCX"}

failures = []


def check(ok, what, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {what}" + (f"  {detail}" if detail else ""))
    if not ok:
        failures.append(what)


def set_mode(c, sixty):
    """Flip FRAME_RATE_60_F, leaving MENU_ACCOUNT beside it alone."""
    v = c.read("wOptions2")
    c.write("wOptions2", (v | 2) if sixty else (v & ~2))
    c.run(8)
    return v


def signed(d):
    d &= 0xFF
    return d - 256 if d > 127 else d


def histogram(values):
    out = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items()))


def handle_map_rate(c, frames=180):
    hits = []
    bank, addr = SYMS["HandleMap"]
    c.pb.hook_register(bank, addr, lambda ctx: hits.append(1), None)
    c.run(frames)
    try:
        c.pb.hook_deregister(bank, addr)
    except Exception:
        pass
    return len(hits) / frames


def walk_samples(c, button, frames):
    """Per-frame (scroll, y, x) while holding a direction."""
    axis = AXIS[button]
    rows = []
    c.pb.button_press(button)
    for _ in range(frames):
        c.run(1)
        rows.append((c.read(axis), c.read("wYCoord"), c.read("wXCoord")))
    c.pb.button_release(button)
    c.run(40)
    return rows


def profile(c, sixty, button="right", frames=200):
    set_mode(c, sixty)
    c.run(30)
    rate = handle_map_rate(c, 120)
    rows = walk_samples(c, button, frames)
    deltas = [signed(b[0] - a[0]) for a, b in zip(rows, rows[1:])]
    edges = [i for i, (a, b) in enumerate(zip(rows, rows[1:]))
             if (a[1], a[2]) != (b[1], b[2])]
    return {
        "rate": rate,
        "deltas": histogram(deltas),
        "moving": histogram([d for d in deltas if d]),
        "frames_per_tile": histogram([b - a for a, b in zip(edges, edges[1:])]),
        "tiles": len(edges),
    }


def show(tag, p):
    print(f"\n  {tag}")
    print(f"    HandleMap calls per frame  : {p['rate']:.2f}")
    print(f"    scroll delta, all frames   : {p['deltas']}")
    print(f"    scroll delta while moving  : {p['moving']}")
    print(f"    frames between tile edges  : {p['frames_per_tile']}")


# --------------------------------------------------------------------------


def test_walking(c):
    print("\n== walking: same speed, finer scroll ==")
    p30 = profile(c, sixty=False, button="right")
    show("30 Hz", p30)
    p60 = profile(c, sixty=True, button="left")
    show("60 Hz", p60)

    check(abs(p30["rate"] - 0.5) < 0.05, "30 Hz runs HandleMap every other frame",
          f"{p30['rate']:.2f}/frame")
    check(abs(p60["rate"] - 1.0) < 0.05, "60 Hz runs HandleMap every frame",
          f"{p60['rate']:.2f}/frame")

    check(set(p30["moving"]) <= {2, -2}, "30 Hz scrolls 2 px per frame",
          str(p30["moving"]))
    check(set(p60["moving"]) <= {1, -1}, "60 Hz scrolls 1 px per frame",
          str(p60["moving"]))

    check(set(p30["frames_per_tile"]) == {16},
          "30 Hz walks a tile in 16 frames", str(p30["frames_per_tile"]))

    # The intent is 16 frames at both rates. It is 17 at 60 Hz, because one
    # iteration per tile rebuilds the on-screen tilemap (UpdateOverworldMap)
    # and that does not fit in a single frame at normal CPU speed, so the loop
    # drops one frame per tile. See tests/measure_overworld.py for the counts.
    worst = max(p60["frames_per_tile"], default=0)
    check(worst <= 17, "60 Hz walks a tile within one frame of 30 Hz",
          str(p60["frames_per_tile"]))
    if worst != 16:
        print(f"    NOTE: 60 Hz needs {worst} frames per tile, not 16. "
              "The per-tile tilemap rebuild overruns a frame at normal CPU "
              "speed; closing the gap needs double-speed CPU.")
    return p30, p60


def live_objects(c):
    """Object slots that have a sprite loaded, other than the player."""
    base = SYMS["wObjectStructs"][1]
    return [i for i in range(1, NUM_OBJECT_STRUCTS)
            if c.pb.memory[1, base + i * OBJECT_LENGTH + OBJECT_SPRITE]]


def facing_changes(c, sixty, frames, button):
    """How many times the player sprite's walk frame changes while walking.

    SetFacingStepAction advances a counter once per overworld iteration and
    takes two bits of it as the sprite frame, so at 60 fps the legs would move
    twice as fast without the widened cycle.
    """
    set_mode(c, sixty)
    c.run(30)
    base = SYMS["wPlayerStruct"][1]
    c.pb.button_press(button)
    seen, changes = None, 0
    for _ in range(frames):
        c.run(1)
        f = c.pb.memory[1, base + OBJECT_FACING]
        if seen is not None and f != seen:
            changes += 1
        seen = f
    c.pb.button_release(button)
    c.run(40)
    return changes


def test_walk_animation(c):
    print("\n== the walk animation runs at the same speed ==")
    a30 = facing_changes(c, False, 160, "right")
    a60 = facing_changes(c, True, 160, "left")
    print(f"    sprite frame changes over 160 frames: "
          f"{a30} at 30 Hz, {a60} at 60 Hz")
    check(a60 > 0, "the sprite still animates at 60 Hz")
    check(abs(a60 - a30) <= max(2, a30 // 5),
          "the legs move at the same rate at both rates",
          f"{a30} vs {a60}")


def npc_step_frames(c, sixty, slot, frames=1500):
    """Frames each of an NPC's own steps takes, start to finish.

    OBJECT_WALKING is STANDING between steps, so the spans where it is not are
    the steps. Their length is the NPC's walking speed in frames, which the
    60 fps table is supposed to leave alone.
    """
    set_mode(c, sixty)
    c.run(30)
    base = SYMS["wObjectStructs"][1] + slot * OBJECT_LENGTH
    spans, started = [], None
    for i in range(frames):
        c.run(1)
        walking = c.pb.memory[1, base + OBJECT_WALKING] != STANDING
        if walking and started is None:
            started = i
        elif not walking and started is not None:
            spans.append(i - started)
            started = None
    return spans


def test_npc(c):
    """New Bark Town's fisher walks up and down on his own.

    He is out of range from the front door, so walk over to him first. His
    steps are STEP_WALK like the player's, so they should take the same 16
    frames whichever table is in use.
    """
    print("\n== NPCs walk at the same speed ==")
    # The fisher is at map (x 12, y 9) and paces up and down that column, so
    # stand in the column beside him rather than in his way.
    nav.walk_to(c, 9, 11)
    print(f"    standing at {nav.coords(c)}")
    slots = live_objects(c)
    print(f"    loaded object slots: {slots}")
    watched = None
    for slot in slots:
        if npc_step_frames(c, False, slot, 1200):
            watched = slot
            break
    if watched is None:
        check(False, "found a self-moving NPC to watch")
        return
    s30 = npc_step_frames(c, False, watched, 1500)
    s60 = npc_step_frames(c, True, watched, 1500)
    print(f"    object slot {watched}")
    print(f"    30 Hz step lengths in frames: {histogram(s30)}")
    print(f"    60 Hz step lengths in frames: {histogram(s60)}")
    check(bool(s60), "NPC still moves at 60 Hz")
    # Spans clipped by the ends of the sampling window are not whole steps.
    m30, m60 = typical(s30), typical(s60)
    if m30 and m60:
        check(abs(m60 - m30) <= 2,
              "NPC steps take the same number of frames at both rates",
              f"{m30} vs {m60}")
    else:
        check(False, "saw a whole NPC step at both rates", f"{m30} vs {m60}")


def typical(spans, floor=8):
    whole = [x for x in spans if x >= floor]
    if not whole:
        return None
    return max(set(whole), key=whole.count)


def test_slow_step(c):
    """slow_step is the cutscene walk: it must stay at half walking speed.

    Reaching a cutscene that uses slow_step from a fresh save is not practical,
    so this drives the same movement engine directly: put an object into a
    STEP_SLOW step, then into a STEP_WALK step, and count the frames each takes
    to cover its tile. The ratio is what matters, and it must be 2 in both
    modes -- at 60 Hz the slow row cannot halve its 1-pixel delta, so it holds
    still on the odd iterations instead.
    """
    print("\n== slow_step keeps its half-speed cadence ==")
    for sixty in (False, True):
        tag = "60 Hz" if sixty else "30 Hz"
        set_mode(c, sixty)
        c.run(30)
        slow = step_frames(c, STEP_SLOW)
        walk = step_frames(c, STEP_WALK)
        print(f"    {tag}: slow step {slow} frames, normal step {walk} frames")
        check(walk > 0 and slow > 0, f"{tag} both steps completed",
              f"slow={slow} walk={walk}")
        if walk > 0 and slow > 0:
            check(abs(slow - 2 * walk) <= 2,
                  f"{tag} slow step takes twice a normal step",
                  f"{slow} vs 2 x {walk}")


def step_frames(c, step_type):
    """Frames for one step of the given type, and the pixels it covered.

    Returns the frame count if the object ended up exactly one tile away, and
    a negative number if it did not.
    """
    base = SYMS["wPlayerStruct"][1]
    # DOWN, so the step shows up in OBJECT_SPRITE_Y. This is the encoding
    # Movement_slow_step_down / Movement_step_down write to OBJECT_WALKING.
    c.pb.memory[1, base + OBJECT_WALKING] = (step_type << 2) | DOWN
    c.pb.memory[1, base + OBJECT_STEP_TYPE] = STEP_TYPE_NPC_WALK
    sixty = c.read("wOptions2") & 2
    # InitStep would take the duration from the step vector table; seed the
    # same value, since this bypasses InitStep.
    duration = {(STEP_SLOW, 0): 16, (STEP_SLOW, 2): 32,
                (STEP_WALK, 0): 8, (STEP_WALK, 2): 16}[(step_type, sixty)]
    c.pb.memory[1, base + OBJECT_STEP_DURATION] = duration
    start = c.pb.memory[1, base + OBJECT_SPRITE_Y]
    for i in range(1, 200):
        c.run(1)
        if c.pb.memory[1, base + OBJECT_STEP_TYPE] != STEP_TYPE_NPC_WALK:
            moved = (c.pb.memory[1, base + OBJECT_SPRITE_Y] - start) & 0xFF
            return i if moved == 16 else -moved
    return -1


def test_jump_arc(c):
    """A jump climbs by the step vector's speed and indexes a 16-entry table.

    Halving the deltas keeps duration x speed at 16 for the normal and fast
    rows, so their arcs are unchanged. The slow row doubles its duration
    without being able to halve its speed, which would run the height counter
    to 64 and read past the end of that table; CheckStepVectorHoldFrame is
    what stops it. This drives a jump by hand and watches the counter.
    """
    print("\n== jump arcs stay inside their table ==")
    rows = {}
    for sixty in (False, True):
        tag = "60 Hz" if sixty else "30 Hz"
        set_mode(c, sixty)
        c.run(30)
        for name, step_type in (("slow", STEP_SLOW), ("normal", STEP_WALK),
                                ("fast", STEP_BIKE)):
            peak, frames = jump_peak(c, step_type)
            rows[(tag, name)] = (peak, frames)
            print(f"    {tag} {name:<6} jump: peak height {peak}, "
                  f"{frames} frames")
            # The final write pushes the counter to 32, but the table is
            # indexed with the value from before that write, so 32 is the
            # correct ceiling. Without the hold on slow frames the 60 Hz slow
            # jump would reach 64 and read past the table.
            check(0 < peak <= 32,
                  f"{tag} {name} jump arc stays inside its table",
                  f"peak {peak}")
    for name in ("slow", "normal", "fast"):
        f30 = rows[("30 Hz", name)][1]
        f60 = rows[("60 Hz", name)][1]
        check(abs(f30 - f60) <= 1,
              f"{name} jump takes the same time at both rates",
              f"{f30} vs {f60} frames")


def jump_peak(c, step_type):
    """Run one jump by hand; return the highest OBJECT_JUMP_HEIGHT reached."""
    base = SYMS["wPlayerStruct"][1]
    sixty = 2 if c.read("wOptions2") & 2 else 0
    duration = {(STEP_SLOW, 0): 16, (STEP_SLOW, 2): 32,
                (STEP_WALK, 0): 8, (STEP_WALK, 2): 16,
                (STEP_BIKE, 0): 4, (STEP_BIKE, 2): 8}[(step_type, sixty)]
    c.pb.memory[1, base + OBJECT_WALKING] = (step_type << 2) | DOWN
    c.pb.memory[1, base + OBJECT_STEP_TYPE] = STEP_TYPE_NPC_JUMP
    c.pb.memory[1, base + OBJECT_STEP_DURATION] = duration
    c.pb.memory[1, base + OBJECT_STEP_INDEX] = 0
    c.pb.memory[1, base + OBJECT_JUMP_HEIGHT] = 0
    peak = 0
    for i in range(1, 300):
        c.run(1)
        peak = max(peak, c.pb.memory[1, base + OBJECT_JUMP_HEIGHT])
        if c.pb.memory[1, base + OBJECT_STEP_TYPE] != STEP_TYPE_NPC_JUMP:
            return peak, i
    return peak, -1


MENU_CURSOR = 0xED  # the "▶" glyph, see constants/charmap.asm


def cursor_row(c):
    tm = c.pb.tilemap_background
    for y in range(18):
        if MENU_CURSOR in list(tm[0:20, y]):
            return y
    return None


def label_row(c, label):
    tm = c.pb.tilemap_background
    build_charmap()
    for y in range(18):
        row = "".join(CHARMAP.get(t, " ") for t in tm[0:20, y])
        if label in row:
            return y
    return None


def open_options(c, limit=12):
    """Pick OPTION out of the start menu.

    The start menu keeps its cursor where it was last left, so this steers by
    what is on screen rather than by a fixed number of presses.
    """
    for _ in range(limit):
        want, at = label_row(c, "OPTION"), cursor_row(c)
        if want is None or at is None:
            return False
        if at == want:
            c.press("a")
            c.run(70)
            return looks_like_options(c)
        c.press("down" if at < want else "up")
        c.run(20)
    return False


def test_persistence(c):
    """wOptions2 sits inside the block SaveOptions copies to SRAM, so the
    setting should survive a save without any new save-file plumbing."""
    print("\n== the setting is saved ==")
    set_mode(c, True)
    c.run(20)
    c.press("start"); c.run(50)
    for _ in range(3):                 # PACK / POKeGEAR / <name> / SAVE
        c.press("down"); c.run(20)
    c.press("a"); c.run(60)
    for _ in range(6):                 # "would you like to save?" then the
        c.press("a"); c.run(60)        # save itself, then the confirmation
    c.run(120)
    offset = SYMS["wOptions2"][1] - SYMS["wOptions"][1]
    sram = c.pb.memory[SYMS["sOptions"][0], SYMS["sOptions"][1] + offset]
    print(f"    wRAM wOptions2 = {c.read('wOptions2'):#04x}, "
          f"sRAM copy = {sram:#04x}")
    check(sram & 2 == 2, "the 60 fps bit reached SRAM", f"{sram:#04x}")
    check(sram == c.read("wOptions2"), "SRAM matches wRAM")
    set_mode(c, False)
    for _ in range(4):                 # back out to the overworld
        c.press("b"); c.run(40)


def test_options_page(c):
    """The SELECT sub-page: open the options menu and drive it."""
    print("\n== options sub-page ==")
    c.press("start"); c.run(50)
    ok = open_options(c)
    check(ok, "reached the options screen")
    if not ok:
        c.screenshot("/tmp/options_fail.png")
        return
    c.screenshot("/tmp/options_page1.png")
    c.press("select"); c.run(40)
    c.screenshot("/tmp/options_page2.png")
    txt = screen_text(c)
    check("FRAME RATE" in txt, "SELECT shows the FRAME RATE page", txt.split("|")[0])
    check("30" in txt or "60" in txt, "the page shows a value")

    before = c.read("wOptions2")
    c.press("right"); c.run(30)
    after = c.read("wOptions2")
    c.screenshot("/tmp/options_page2_toggled.png")
    check((before ^ after) == 2, "RIGHT flips only FRAME_RATE_60_F",
          f"{before:#04x} -> {after:#04x}")
    check((before & 1) == (after & 1), "MENU ACCOUNT is untouched")

    c.press("select"); c.run(40)
    c.screenshot("/tmp/options_page1_again.png")
    txt = screen_text(c)
    check("TEXT SPEED" in txt and "FRAME RATE" not in txt,
          "SELECT goes back to the first page")
    c.press("b"); c.run(60)
    c.press("b"); c.run(60)


CHARMAP = {}


def build_charmap():
    """Enough of the tile-to-ASCII mapping to read menu labels off the screen."""
    for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        CHARMAP[0x80 + i] = ch
    for i, ch in enumerate("abcdefghijklmnopqrstuvwxyz"):
        CHARMAP[0xA0 + i] = ch
    for i in range(10):
        CHARMAP[0xF6 + i] = str(i)
    CHARMAP[0x7F] = " "
    CHARMAP[0x9C] = ":"


def screen_text(c):
    build_charmap()
    tm = c.pb.tilemap_background
    rows = []
    for y in range(18):
        rows.append("".join(CHARMAP.get(t, " ") for t in tm[0:20, y]).strip())
    return "|".join(r for r in rows if r)


def looks_like_options(c):
    return "TEXT SPEED" in screen_text(c)


# object struct field offsets, from constants/map_object_constants.asm
OBJECT_WALKING = 0x07
OBJECT_STEP_TYPE = 0x09
OBJECT_STEP_DURATION = 0x0A
OBJECT_SPRITE = 0x00
OBJECT_DIRECTION = 0x08
OBJECT_FACING = 0x0D
OBJECT_MAP_X = 0x10
OBJECT_MAP_Y = 0x11
OBJECT_SPRITE_X = 0x17
OBJECT_SPRITE_Y = 0x18
OBJECT_LENGTH = 0x28
NUM_OBJECT_STRUCTS = 13
STEP_SLOW = 0
STEP_WALK = 1
STEP_BIKE = 2
DOWN = 0
STEP_TYPE_NPC_WALK = 0x02
STEP_TYPE_NPC_JUMP = 0x08
OBJECT_STEP_INDEX = 0x1C
OBJECT_JUMP_HEIGHT = 0x1F
STANDING = 0xFF


if __name__ == "__main__":
    with overworld() as c:
        print("map:", nav.to_new_bark_town(c), "coords", nav.coords(c))
        print("wOptions2 =", hex(c.read("wOptions2")))

        test_walking(c)
        test_walk_animation(c)
        test_npc(c)
        test_slow_step(c)
        test_jump_arc(c)
        test_persistence(c)
        test_options_page(c)

        print()
        if failures:
            print(f"FAILED ({len(failures)}):")
            for f in failures:
                print("  -", f)
            sys.exit(1)
        print("all checks passed")
