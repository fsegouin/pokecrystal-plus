"""Checks for the running shoes.

Holding B while walking on foot steps at the bike's speed instead of the
walking speed. Nothing gates it: no item, no badge, no option.

The checks are:
  * a run covers a tile in half the frames a walk does, at both frame rates;
  * a run takes the same wall clock time in both, the way a walk does;
  * releasing B goes straight back to the walking speed;
  * B while standing still moves nothing, and still cancels a menu;
  * the bike, surfing, ice, ledges, bumps and forced movement all pick the
    same step with B held as without it;
  * the bike rows of both step tables are the vanilla bytes, untouched;
  * the walk animation keeps pace with the feet while running;
  * a running step still gets one trainer sight check per tile, so running
    cannot slip past a trainer a walk would have been caught by.

The speed checks walk the east-west stretch the Goldenrod saves start on.
The step-choice checks call DoPlayerMovement on its own instead, with the
player state and the tile collisions written by hand: that reaches surfing,
ice and ledges without needing a save state parked on each of them, and it
reads the movement command the routine picked rather than inferring it.

Run: .venv/bin/python tests/test_running.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import STATES, Crystal, load_symbols  # noqa: E402

SYMS = load_symbols()

PAD_B = 1 << 1
PAD_RIGHT = 1 << 4

# wPlayerState values, from constants/ram_constants.asm
PLAYER_NORMAL = 0
PLAYER_BIKE = 1
PLAYER_SKATE = 2
PLAYER_SURF = 4
PLAYER_SURF_PIKA = 8

# collision ids, from constants/collision_constants.asm
COLL_FLOOR = 0x00
COLL_ICE = 0x23
COLL_WATER = 0x29
COLL_WATERFALL = 0x33
COLL_HOP_RIGHT = 0xA0

# FACE_RIGHT in wTilePermissions blocks a step to the right
FACE_RIGHT = 1

# movement command ids, from macros/scripts/movement.asm
MOVEMENT = {
    0x0F: "step_right",
    0x13: "big_step_right",
    0x1F: "fast_slide_step_right",
    0x33: "jump_step_right",
    0x50: "step_bump",
    0x0C: "step_down",
    0x5D: "run_step_right",
}

# wPlayerDirection value for facing right, so no check turns in place first
OW_RIGHT = 3 << 2

# object struct field offsets, from constants/map_object_constants.asm
OBJECT_FACING = 0x0D

failures = []


def check(ok, what, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {what}" + (f"  {detail}" if detail else ""))
    if not ok:
        failures.append(what)


def name_of(cmd):
    return MOVEMENT.get(cmd, f"${cmd:02x}")


# --- measuring real movement ------------------------------------------------

def park(c, direction="left", frames=300):
    """Walk into the wall at one end of the stretch, so every measurement
    starts from the same tile with the same run-up available."""
    c.pb.button_press(direction)
    c.run(frames)
    c.pb.button_release(direction)
    c.run(40)


def trace(c, buttons, frames=140):
    """Per-frame (y, x, sprite facing, trainer checks so far) while holding
    `buttons`, windowed to the frames between the first and last tile edge so
    that the idle time after the player hits the far wall is left out."""
    base = c.syms["wPlayerStruct"][1]
    checks = [0]
    bank, addr = SYMS["CheckTrainerBattle"]
    c.pb.hook_register(bank, addr, lambda ctx: checks.__setitem__(0, checks[0] + 1), None)
    rows = []
    for b in buttons:
        c.pb.button_press(b)
    for _ in range(frames):
        c.run(1)
        rows.append((c.read("wYCoord"), c.read("wXCoord"),
                     c.pb.memory[1, base + OBJECT_FACING], checks[0]))
    for b in buttons:
        c.pb.button_release(b)
    c.run(20)
    c.pb.hook_deregister(bank, addr)

    edges = [i for i, (a, b) in enumerate(zip(rows, rows[1:])) if a[:2] != b[:2]]
    assert len(edges) >= 3, f"only {len(edges)} tile edges in {frames} frames"
    lo, hi = edges[0], edges[-1]
    tiles = len(edges) - 1
    window = rows[lo:hi + 1]
    gaps = sorted({b - a for a, b in zip(edges, edges[1:])})
    return {
        "tiles": tiles,
        "frames_per_tile": gaps,
        "anim_per_tile": sum(1 for a, b in zip(window, window[1:])
                             if a[2] != b[2]) / tiles,
        "checks_per_tile": (rows[hi][3] - rows[lo][3]) / tiles,
    }


def measure(c, label, buttons, state=PLAYER_NORMAL, frames=140):
    park(c)
    c.write("wPlayerState", state)
    c.run(4)
    p = trace(c, buttons, frames)
    c.write("wPlayerState", PLAYER_NORMAL)
    c.run(4)
    print(f"    {label:14s} frames/tile {p['frames_per_tile']}"
          f"  sprite frames/tile {p['anim_per_tile']:.2f}"
          f"  sight checks/tile {p['checks_per_tile']:.2f}")
    return p


# --- driving DoPlayerMovement on its own ------------------------------------

def pick_step(c, b, state=PLAYER_NORMAL, tile_ahead=COLL_FLOOR,
              tile_under=COLL_FLOOR, perms=0):
    """The movement command DoPlayerMovement picks for a step to the right."""
    c.write("wPlayerState", state)
    c.write("wTilePermissions", perms)
    c.write("wTileRight", tile_ahead)
    c.write("wPlayerTileCollision", tile_under)
    c.write("wBikeFlags", 0)
    c.write("wPlayerDirection", OW_RIGHT)
    c.write("wPlayerTurningDirection", 0)
    c.pb.memory[c.addr("hJoyDown")] = PAD_RIGHT | (PAD_B if b else 0)
    c.farcall("DoPlayerMovement")
    return c.read("wMovementAnimation")


# --- the checks -------------------------------------------------------------

def test_speed(c, tag):
    print(f"\n== {tag}: a run covers a tile in half the frames ==")
    walk = measure(c, "walk", ["right"])
    run = measure(c, "run (B held)", ["right", "b"])
    bike = measure(c, "bike", ["right"], state=PLAYER_BIKE)
    bike_b = measure(c, "bike (B held)", ["right", "b"], state=PLAYER_BIKE)

    check(walk["frames_per_tile"] == [16], f"{tag}: a walk takes 16 frames a tile",
          str(walk["frames_per_tile"]))
    check(run["frames_per_tile"] == [8], f"{tag}: a run takes 8 frames a tile",
          str(run["frames_per_tile"]))
    check(bike["frames_per_tile"] == [8], f"{tag}: the bike still takes 8 frames a tile",
          str(bike["frames_per_tile"]))
    check(bike_b["frames_per_tile"] == bike["frames_per_tile"],
          f"{tag}: B does nothing on the bike",
          f"{bike['frames_per_tile']} vs {bike_b['frames_per_tile']}")

    # the legs have to keep pace with the feet: a run advances the animation
    # counter twice as fast, so a tile shows about as many sprite frames as a
    # walking tile does, rather than the one a vanilla big step shows.
    check(run["anim_per_tile"] >= walk["anim_per_tile"] - 0.5,
          f"{tag}: the legs keep pace with a run",
          f"{run['anim_per_tile']:.2f} vs {walk['anim_per_tile']:.2f} walking")
    check(run["anim_per_tile"] > bike["anim_per_tile"],
          f"{tag}: a run animates faster than a big step",
          f"{run['anim_per_tile']:.2f} vs {bike['anim_per_tile']:.2f}")

    # trainer sight is checked once per completed step, not once per frame, so
    # covering a tile in half the time does not halve the chances of being seen.
    for label, p in (("walk", walk), ("run", run)):
        check(abs(p["checks_per_tile"] - 1.0) < 0.01,
              f"{tag}: a {label} gets one trainer sight check a tile",
              f"{p['checks_per_tile']:.2f}")

    # releasing B goes straight back to the walking speed
    park(c)
    back = trace(c, ["right", "b"], 40)
    park(c)
    after = trace(c, ["right"], 140)
    check(back["frames_per_tile"] == [8] and after["frames_per_tile"] == [16],
          f"{tag}: releasing B goes back to the walking speed",
          f"{back['frames_per_tile']} then {after['frames_per_tile']}")
    return walk, run, bike


def test_standing_still(c):
    print("\n== B while standing still ==")
    before = (c.read("wYCoord"), c.read("wXCoord"), c.read("hSCX"), c.read("hSCY"))
    c.pb.button_press("b")
    c.run(120)
    c.pb.button_release("b")
    c.run(20)
    after = (c.read("wYCoord"), c.read("wXCoord"), c.read("hSCX"), c.read("hSCY"))
    check(before == after, "B alone moves nothing", f"{before} -> {after}")
    check(c.read("wScriptRunning") == 0, "B alone starts no script")

    c.press("start")
    c.run(40)
    opened = c.read("wScriptRunning") != 0
    c.press("b")
    c.run(60)
    closed = c.read("wScriptRunning") == 0
    check(opened and closed, "B still backs out of the start menu")


def test_other_states(c):
    print("\n== every other kind of step ignores B ==")
    cases = [
        ("on foot",         dict()),
        ("bike",            dict(state=PLAYER_BIKE)),
        ("skateboard",      dict(state=PLAYER_SKATE)),
        ("surfing",         dict(state=PLAYER_SURF, tile_ahead=COLL_WATER)),
        ("surfing on pika", dict(state=PLAYER_SURF_PIKA, tile_ahead=COLL_WATER)),
        ("sliding on ice",  dict(tile_under=COLL_ICE)),
        ("hopping a ledge", dict(tile_under=COLL_HOP_RIGHT, perms=FACE_RIGHT)),
        ("bumping a wall",  dict(perms=FACE_RIGHT)),
        ("on a waterfall",  dict(tile_under=COLL_WATERFALL)),
    ]
    picked = {}
    for label, kw in cases:
        without = pick_step(c, False, **kw)
        with_b = pick_step(c, True, **kw)
        picked[label] = (without, with_b)
        print(f"    {label:16s} {name_of(without):22s} B held: {name_of(with_b)}")
    c.write("wPlayerState", PLAYER_NORMAL)

    check(picked["on foot"] == (0x0F, 0x5D),
          "on foot, B turns a step into a run step",
          f"{name_of(picked['on foot'][0])} / {name_of(picked['on foot'][1])}")
    for label, _ in cases[1:]:
        without, with_b = picked[label]
        check(without == with_b, f"{label}: B changes nothing",
              f"{name_of(without)} / {name_of(with_b)}")


def test_step_tables(c):
    """The bike rows of both tables have to be the vanilla bytes: running
    borrows the bike's speed rather than changing it."""
    print("\n== the step tables ==")
    # x, y, duration, speed, four directions to a row; see StepVectors in
    # engine/overworld/map_objects.asm
    VANILLA_BIKE = [0, 4, 4, 4, 0, -4, 4, 4, -4, 0, 4, 4, 4, 0, 4, 4]
    VANILLA_BIKE_60 = [0, 2, 8, 2, 0, -2, 8, 2, -2, 0, 8, 2, 2, 0, 8, 2]

    def rows(symbol, tier):
        bank, addr = SYMS[symbol]
        raw = [c.pb.memory[bank, addr + tier * 16 + i] for i in range(16)]
        return [b - 256 if b > 127 else b for b in raw]

    STEP_BIKE, STEP_RUN = 2, 3
    for symbol, vanilla in (("StepVectors", VANILLA_BIKE),
                            ("StepVectors60", VANILLA_BIKE_60)):
        bike = rows(symbol, STEP_BIKE)
        run = rows(symbol, STEP_RUN)
        check(bike == vanilla, f"{symbol}: the bike row is unchanged", str(bike))
        check(run == bike, f"{symbol}: the running row matches the bike row", str(run))


def main():
    print("== running shoes ==")
    results = {}
    for tag, sav, sixty in (("30 fps", "fps30.sav", False),
                            ("60 fps", "fps60.sav", True)):
        path = os.path.join(STATES, sav)
        if not os.path.exists(path):
            print(f"  [SKIP] {path} is missing")
            failures.append(f"{sav} is missing")
            continue
        with Crystal(sav=path) as c:
            c.continue_game()
            got = bool(c.read("wOptions2") & 2)
            check(got == sixty, f"{sav} is a {tag} save", f"60 fps bit = {got}")
            results[tag] = test_speed(c, tag)
            test_standing_still(c)
            if not sixty:
                test_other_states(c)
                test_step_tables(c)

    if len(results) == 2:
        print("\n== the same wall clock speed in both modes ==")
        for i, label in enumerate(("walk", "run", "bike")):
            a = results["30 fps"][i]["frames_per_tile"]
            b = results["60 fps"][i]["frames_per_tile"]
            check(a == b, f"a {label} takes the same frames a tile in both modes",
                  f"{a} vs {b}")

    print()
    if failures:
        print(f"{len(failures)} FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
