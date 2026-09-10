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
  * a slow_step still takes twice as long as a normal step, in both modes;
  * every other overworld duration counted in loop iterations (pauses, turns,
    teleports, skyfalls, the fishing bite, the screen shake, the map name sign)
    lasts the same number of frames in both modes;
  * every sprite animation driven by the same loop cycles at the same rate.

Run: .venv/bin/python tests/test_fps.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nav  # noqa: E402
from boot import overworld  # noqa: E402
from harness import ROM, load_symbols  # noqa: E402

SYMS = load_symbols()
FRAME_RATE_60_F = 1
MENU_ACCOUNT = 0

# hSCX and hSCY are the shadow copies the VBlank handler writes to the real
# scroll registers, so they carry the value the overworld loop computed.
AXIS = {"up": "hSCY", "down": "hSCY", "left": "hSCX", "right": "hSCX"}

# object struct field offsets, from constants/map_object_constants.asm
OBJECT_WALKING = 0x07
OBJECT_STEP_TYPE = 0x09
OBJECT_STEP_DURATION = 0x0A
OBJECT_SPRITE = 0x00
OBJECT_FACING = 0x0D
OBJECT_MAP_X = 0x10
OBJECT_MAP_Y = 0x11
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
OBJECT_MAP_OBJECT_INDEX = 0x01
OBJECT_ACTION = 0x0B
OBJECT_STEP_FRAME = 0x0C
OBJECT_LAST_MAP_X = 0x12
OBJECT_LAST_MAP_Y = 0x13
OBJECT_INIT_X = 0x14
OBJECT_INIT_Y = 0x15
OBJECT_SPRITE_X_OFFSET = 0x19
OBJECT_SPRITE_Y_OFFSET = 0x1A
OBJECT_RANGE = 0x20
STEP_TYPE_FROM_MOVEMENT = 0x01
STEP_TYPE_STANDING = 0x04
STEP_TYPE_TURN = 0x0A
STEP_TYPE_TELEPORT_FROM = 0x0C
STEP_TYPE_TELEPORT_TO = 0x0D
STEP_TYPE_SKYFALL = 0x0E
STEP_TYPE_GOT_BITE = 0x10
STEP_TYPE_SKYFALL_TOP = 0x19
OBJECT_ACTION_STAND = 0x01
OBJECT_ACTION_BUMP = 0x03
OBJECT_ACTION_SPIN = 0x04
OBJECT_ACTION_BOUNCE = 0x0A
OBJECT_ACTION_WEIRD_TREE = 0x0B
OBJECT_ACTION_BOULDER_DUST = 0x0E
OBJECT_ACTION_GRASS_SHAKE = 0x0F
OBJECT_ACTION_SKYFALL = 0x10
SHAKE_SLOT = 6  # an object slot New Bark Town leaves empty

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

    # 16 frames at both rates. The one iteration per tile that rebuilds the
    # on-screen tilemap (UpdateOverworldMap) does not fit in a single frame at
    # normal CPU speed, which used to cost a held frame at every tile boundary;
    # the option now runs the CGB in double speed, which halves that iteration
    # and closes the gap. See tests/measure_overworld.py for the counts.
    check(set(p60["frames_per_tile"]) == {16},
          "60 Hz walks a tile in 16 frames", str(p60["frames_per_tile"]))
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


# --------------------------------------------------------------------------
# Everything below counts a duration in overworld loop iterations rather than
# frames. At 60 Hz there are twice as many iterations per second, so each of
# these has to be doubled where it is written for the effect to last the same
# wall clock time.


def frames_until(c, pred, limit=800):
    for i in range(1, limit + 1):
        c.run(1)
        if pred():
            return i
    return -1


def call_with_bc(c, routine, struct=None, frames=4):
    """Run one ROM routine with bc pointing at an object struct, then put the
    overworld loop back where it was.

    harness.farcall parks the CPU on a trap when the routine returns, which on
    its own would end the run. Saving the registers first and restoring them
    afterwards lets the loop carry on from the instruction it was interrupted
    at, so the effect the routine set up can then be timed.
    """
    rf = c.pb.register_file
    saved = (rf.A, rf.F, rf.B, rf.C, rf.D, rf.E, rf.HL, rf.SP, rf.PC)
    if struct is not None:
        rf.B, rf.C = struct >> 8, struct & 0xFF
    c.farcall(routine, frames)
    (rf.A, rf.F, rf.B, rf.C, rf.D, rf.E, rf.HL, rf.SP, rf.PC) = saved


def call_returning_a(c, routine, frames=4):
    """Run one ROM routine and hand back what it left in a.

    harness.farcall goes through the game's own rst FarCall, which returns with
    a holding c, so a routine that answers in a would lose its answer. This
    pages the routine's bank in by hand and calls it directly instead.
    """
    pb, rf = c.pb, c.pb.register_file
    bank, addr = SYMS[routine]
    trap = SYMS["hMathBuffer"][1]
    pb.memory[trap] = 0x18      # jr -2
    pb.memory[trap + 1] = 0xFE
    saved = (rf.A, rf.F, rf.B, rf.C, rf.D, rf.E, rf.HL, rf.SP, rf.PC)
    saved_ie = pb.memory[0xFFFF]
    saved_bank = pb.memory[SYMS["hROMBank"][1]]
    pb.memory[0xFFFF] = 0       # mask every interrupt
    pb.memory[0x2000] = bank    # a write down here is an MBC command
    sp = rf.SP - 2
    pb.memory[sp] = trap & 0xFF
    pb.memory[sp + 1] = trap >> 8
    rf.SP = sp
    rf.PC = addr
    c.run(frames)
    if rf.PC != trap:
        raise RuntimeError(f"{routine} did not return within {frames} frames "
                           f"(PC=${rf.PC:04x})")
    result = rf.A
    pb.memory[0x2000] = saved_bank
    pb.memory[0xFFFF] = saved_ie
    (rf.A, rf.F, rf.B, rf.C, rf.D, rf.E, rf.HL, rf.SP, rf.PC) = saved
    return result


def release_player(c):
    """Hand the player object back to the movement engine.

    Its own copy of the coordinates gets put straight at the same time: the
    checks that drive steps by hand leave it several tiles from the camera, and
    an object the engine decides is off screen stops being animated at all.
    """
    base = SYMS["wPlayerStruct"][1]
    m = c.pb.memory
    x = c.read("wXCoord") + 4
    y = c.read("wYCoord") + 4
    for field in (OBJECT_MAP_X, OBJECT_LAST_MAP_X, OBJECT_INIT_X):
        m[1, base + field] = x
    for field in (OBJECT_MAP_Y, OBJECT_LAST_MAP_Y, OBJECT_INIT_Y):
        m[1, base + field] = y
    m[1, base + OBJECT_SPRITE_X_OFFSET] = 0
    m[1, base + OBJECT_SPRITE_Y_OFFSET] = 0
    m[1, base + OBJECT_ACTION] = OBJECT_ACTION_STAND
    m[1, base + OBJECT_STEP_TYPE] = STEP_TYPE_FROM_MOVEMENT
    c.run(20)


def movement_frames(c, sixty, routine, param=None):
    """Frames the pause set up by one movement command lasts.

    Reaching most of these from a fresh save means finding the one cutscene
    that uses them, so they are driven straight through the movement command,
    the way the jump checks drive a step. A command that reads its duration out
    of the movement stream (rock smash, dig) gets the stream reader pointed at
    GetPlayerNextMovementIndex, which hands back wPlayerNextMovement.
    """
    set_mode(c, sixty)
    c.run(30)
    base = SYMS["wPlayerStruct"][1]
    if param is not None:
        ptr = SYMS["GetPlayerNextMovementIndex"][1]
        c.write("wMovementPointer", ptr & 0xFF)
        c.write("wMovementPointer", ptr >> 8, 1)
        c.write("wPlayerNextMovement", param)
    call_with_bc(c, routine, base)
    m = c.pb.memory
    step = m[1, base + OBJECT_STEP_TYPE]
    n = frames_until(c, lambda: m[1, base + OBJECT_STEP_TYPE] != step)
    release_player(c)
    return n


def self_timed_frames(c, sixty, step_type):
    """Frames a step function that writes its own duration lasts."""
    set_mode(c, sixty)
    c.run(30)
    base = SYMS["wPlayerStruct"][1]
    m = c.pb.memory
    for field in (OBJECT_STEP_INDEX, OBJECT_STEP_FRAME, OBJECT_JUMP_HEIGHT,
                  OBJECT_SPRITE_Y_OFFSET):
        m[1, base + field] = 0
    m[1, base + OBJECT_STEP_TYPE] = step_type
    n = frames_until(c, lambda: m[1, base + OBJECT_STEP_TYPE] != step_type)
    release_player(c)
    return n


# label, routine to drive, movement stream byte it should read
MOVEMENT_DURATIONS = [
    ("step_sleep 3", "Movement_step_sleep_3", None),
    ("step_bump", "Movement_step_bump", None),
    ("tree_shake", "Movement_tree_shake", None),
    ("spin pause", "_MovementSpinRepeat", None),
    ("rock_smash 12", "Movement_rock_smash", 12),
    ("step_dig 12", "Movement_step_dig", 12),
]

STEP_DURATIONS = [
    ("teleport_from", STEP_TYPE_TELEPORT_FROM),
    ("teleport_to", STEP_TYPE_TELEPORT_TO),
    ("skyfall", STEP_TYPE_SKYFALL),
    ("skyfall_top", STEP_TYPE_SKYFALL_TOP),
    ("fishing bite", STEP_TYPE_GOT_BITE),
    ("turn in place", STEP_TYPE_TURN),
]


def test_durations(c):
    print("\n== durations last the same number of frames ==")
    for label, routine, param in MOVEMENT_DURATIONS:
        f30 = movement_frames(c, False, routine, param)
        f60 = movement_frames(c, True, routine, param)
        print(f"    {label:<16} 30 Hz {f30:>4} frames, 60 Hz {f60:>4} frames")
        check(f30 > 0 and f60 > 0, f"{label} completed at both rates",
              f"{f30} vs {f60}")
        check(f30 > 0 and abs(f30 - f60) <= parity_slack(f30),
              f"{label} lasts the same time at both rates", f"{f30} vs {f60}")
    for label, step_type in STEP_DURATIONS:
        f30 = self_timed_frames(c, False, step_type)
        f60 = self_timed_frames(c, True, step_type)
        print(f"    {label:<16} 30 Hz {f30:>4} frames, 60 Hz {f60:>4} frames")
        check(f30 > 0 and f60 > 0, f"{label} completed at both rates",
              f"{f30} vs {f60}")
        check(f30 > 0 and abs(f30 - f60) <= parity_slack(f30),
              f"{label} lasts the same time at both rates", f"{f30} vs {f60}")


def parity_slack(frames):
    """How far apart the two rates may land for a duration this long.

    At 60 Hz an iteration occasionally takes two frames instead of one (the
    tilemap rebuild overruns), so a doubled duration accumulates a little slip
    in proportion to how many iterations it spans. Two frames covers the short
    ones; longer effects need a few percent.
    """
    return max(2, frames // 20)

def screen_shake_frames(c, sixty, rng=16):
    """Frames an earthquake shakes for.

    step_shake spawns its own object, so this fills in a spare object slot and
    runs the movement function on it. The shake ends by deleting that object,
    which is what the frame count waits for.
    """
    set_mode(c, sixty)
    c.run(30)
    m = c.pb.memory
    base = SYMS["wObjectStructs"][1] + SHAKE_SLOT * OBJECT_LENGTH
    for i in range(OBJECT_LENGTH):
        m[1, base + i] = 0
    m[1, base + OBJECT_SPRITE] = 1
    m[1, base + OBJECT_MAP_OBJECT_INDEX] = 0xFF
    # Object coordinates run 4 ahead of wXCoord / wYCoord, and the checks above
    # leave the player struct's own copy stale, so read the camera instead: an
    # object outside the visible range is deleted before it can shake anything.
    x = c.read("wXCoord") + 4
    y = c.read("wYCoord") + 4
    m[1, base + OBJECT_MAP_X] = m[1, base + OBJECT_INIT_X] = x
    m[1, base + OBJECT_MAP_Y] = m[1, base + OBJECT_INIT_Y] = y
    m[1, base + OBJECT_RANGE] = rng
    call_with_bc(c, "MovementFunction_ScreenShake", base)
    return frames_until(c, lambda: m[1, base + OBJECT_SPRITE] == 0)


def test_screen_shake(c):
    print("\n== the screen shake lasts as long ==")
    f30 = screen_shake_frames(c, False)
    f60 = screen_shake_frames(c, True)
    print(f"    earthquake 16: 30 Hz {f30} frames, 60 Hz {f60} frames")
    check(f30 > 0 and f60 > 0, "the shake ran at both rates", f"{f30} vs {f60}")
    check(f30 > 0 and abs(f30 - f60) <= parity_slack(f30),
          "the shake lasts the same time at both rates", f"{f30} vs {f60}")


def sign_frames(c, sixty):
    """Frames the map name sign stays up.

    Crossing a landmark boundary to raise it means walking to the next map,
    and the routine that would raise it on the spot waits on VBlank, so this
    asks the game for the count it would store and stores that. From there it
    is the real sign: PlaceMapNameSign draws it and ticks it down, once per
    overworld iteration.
    """
    set_mode(c, sixty)
    c.run(30)
    started = call_returning_a(c, "MapNameSignFrames60")
    c.write("wLandmarkSignTimer", started)
    if not started:
        return -1, started
    return frames_until(c, lambda: c.read("wLandmarkSignTimer") == 0), started


def test_map_name_sign(c):
    print("\n== the map name sign stays up as long ==")
    f30, t30 = sign_frames(c, False)
    f60, t60 = sign_frames(c, True)
    print(f"    timer starts at {t30} at 30 Hz and {t60} at 60 Hz")
    print(f"    sign visible for {f30} frames at 30 Hz, {f60} at 60 Hz")
    check(f30 > 0 and f60 > 0, "the sign counted down at both rates",
          f"{f30} vs {f60}")
    check(f30 > 0 and abs(f30 - f60) <= 4,
          "the sign stays up the same time at both rates", f"{f30} vs {f60}")


ANIMATIONS = [
    ("bounce", OBJECT_ACTION_BOUNCE),
    ("weird tree", OBJECT_ACTION_WEIRD_TREE),
    ("boulder dust", OBJECT_ACTION_BOULDER_DUST),
    ("grass shake", OBJECT_ACTION_GRASS_SHAKE),
    ("skyfall", OBJECT_ACTION_SKYFALL),
    ("teleport spin", OBJECT_ACTION_SPIN),
    ("bump", OBJECT_ACTION_BUMP),
]


def action_changes(c, sixty, action, frames=180):
    """How often an object action changes the sprite it is showing.

    Each of these advances a counter once per overworld iteration and takes a
    couple of bits of it as the frame, so at 60 Hz they would all run twice as
    fast without AdvanceStepFrame60.
    """
    set_mode(c, sixty)
    c.run(30)
    release_player(c)
    base = SYMS["wPlayerStruct"][1]
    m = c.pb.memory
    m[1, base + OBJECT_STEP_FRAME] = 0
    seen, changes = None, 0
    for _ in range(frames):
        m[1, base + OBJECT_STEP_TYPE] = STEP_TYPE_STANDING
        m[1, base + OBJECT_ACTION] = action
        c.run(1)
        f = m[1, base + OBJECT_FACING]
        if seen is not None and f != seen:
            changes += 1
        seen = f
    release_player(c)
    return changes


def test_animations(c):
    print("\n== sprite animations cycle at the same rate ==")
    for label, action in ANIMATIONS:
        a30 = action_changes(c, False, action)
        a60 = action_changes(c, True, action)
        print(f"    {label:<14} frame changes over 180 frames: "
              f"{a30} at 30 Hz, {a60} at 60 Hz")
        check(a30 > 0, f"{label} animates at 30 Hz", str(a30))
        check(a60 > 0, f"{label} animates at 60 Hz", str(a60))
        check(abs(a60 - a30) <= max(2, a30 // 5),
              f"{label} cycles at the same rate at both rates",
              f"{a30} vs {a60}")


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


def find_hdma_terminate(c):
    """Address of `ld hl, rVDMA_LEN` at the tail of `_continue_HDMATransfer`.

    The routine ends by turning off the HBlank DMA it started. Locating that
    write by its opcodes rather than by a symbol keeps the check working when
    the surrounding code moves."""
    bank, addr = c.syms["_continue_HDMATransfer"]
    with open(ROM, "rb") as f:
        rom = f.read()
    base = bank * 0x4000 + (addr - 0x4000)
    want = bytes([0x21, 0x55, 0xFF])          # ld hl, rVDMA_LEN
    i = rom.index(want, base, base + 0x100)
    return bank, addr + (i - base), rom[i + 3:i + 5]


def test_hdma_terminate(c):
    """Opening a menu must never clear bit 7 of a finished HBlank DMA.

    `rVDMA_LEN` reads $ff once a transfer has run out. Clearing bit 7 of that
    does not stop anything: it writes $7f, which asks for a general purpose DMA
    of 2 KB into VRAM from wherever the finished transfer left its pointers.
    Vanilla armed one block more than it wanted and relied on the transfer
    still being live at this point, a margin of exactly one block that double
    speed can eat. So the routine has to arm exactly what it wants and guard
    the write."""
    print("\n== HBlank DMA terminate ==")
    bank, addr, guard = find_hdma_terminate(c)
    check(guard == bytes([0xCB, 0x7E]),
          "the terminate is guarded by bit 7, [hl]", guard.hex())

    seen = {}
    c.pb.hook_register(bank, addr,
                       lambda ctx: seen.setdefault(ctx, []).append(
                           c.pb.memory[0xFF55]), None)
    for sixty in (False, True):
        set_mode(c, sixty)
        c.run(40)
        seen.clear()
        c.press("start"); c.run(60)
        c.press("b"); c.run(60)
        rate = 60 if sixty else 30
        reads = seen.get(None, [])
        check(bool(reads), f"{rate} fps: the menu ran HBlank DMA transfers",
              f"{len(reads)} of them")
        check(all(v == 0xFF for v in reads),
              f"{rate} fps: every transfer finished on its own",
              sorted({hex(v) for v in reads}))
    set_mode(c, False)


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

if __name__ == "__main__":
    with overworld() as c:
        print("map:", nav.to_new_bark_town(c), "coords", nav.coords(c))
        print("wOptions2 =", hex(c.read("wOptions2")))

        test_walking(c)
        test_walk_animation(c)
        test_npc(c)
        test_slow_step(c)
        test_jump_arc(c)
        test_durations(c)
        test_screen_shake(c)
        test_map_name_sign(c)
        test_animations(c)
        test_persistence(c)
        test_hdma_terminate(c)
        test_options_page(c)

        print()
        if failures:
            print(f"FAILED ({len(failures)}):")
            for f in failures:
                print("  -", f)
            sys.exit(1)
        print("all checks passed")
