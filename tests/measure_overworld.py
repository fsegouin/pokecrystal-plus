"""Measure the overworld loop: how long an iteration takes, and how much of
it fits in a frame.

This is the evidence behind the 60 fps option. HandleMap is the overworld loop
body and it splits around a frame delay:

    HandleMap -> HandleMapTimeAndJoypad -> HandleCmdQueue -> MapEvents
              -> HandleMapObjects -> NextOverworldFrame (the delay)
              -> HandleMapBackground -> CheckPlayerState -> ret

At 30 Hz the delay is two frames, so the work either side of it has two frames
to finish in. At 60 Hz it has one. The question the option turns on is whether
the work fits.

    .venv/bin/python tests/measure_overworld.py cadence   # frames per iteration
    .venv/bin/python tests/measure_overworld.py stages    # cycles per stage
    .venv/bin/python tests/measure_overworld.py           # both
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nav  # noqa: E402
from boot import overworld  # noqa: E402
from harness import load_symbols  # noqa: E402

SYMS = load_symbols()
FRAME_CYCLES = 70224  # t-cycles per frame on a CGB at normal speed

# The stages of one iteration, in call order, plus the sub-calls worth
# attributing separately.
STAGES = [
    "HandleMap",
    "HandleMapTimeAndJoypad",
    "HandleCmdQueue",
    "MapEvents",
    "ScriptEvents",
    "HandleMapObjects",
    "HandleNPCStep",
    "_HandlePlayerStep",
    "UpdateOverworldMap",
    "NextOverworldFrame",
    "HandleMapBackground",
    "_UpdateSprites",
    "ScrollScreen",
    "PlaceMapNameSign",
    "CheckPlayerState",
]


def set_mode(c, sixty):
    v = c.read("wOptions2")
    c.write("wOptions2", (v | 2) if sixty else (v & ~2))
    c.run(20)


def histogram(values):
    out = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items()))


# ---------------------------------------------------------------- cadence


def cadence(c, sixty, button, frames=480):
    """Frames between HandleMap iterations, and between tile steps.

    This is the ground truth: cycle counts sampled inside a hook carry some
    jitter, but the emulated frame number at each hook does not.
    """
    set_mode(c, sixty)
    at, tiles = [], []
    hooks = [(SYMS["HandleMap"], at), (SYMS["UpdateOverworldMap"], tiles)]
    for (bank, addr), sink in hooks:
        c.pb.hook_register(
            bank, addr, (lambda s: lambda ctx: s.append(c.pb.frame_count))(sink),
            None)
    c.pb.button_press(button)
    c.run(frames)
    c.pb.button_release(button)
    c.run(30)
    for (bank, addr), _ in hooks:
        try:
            c.pb.hook_deregister(bank, addr)
        except Exception:
            pass
    return (histogram([b - a for a, b in zip(at, at[1:])]),
            histogram([b - a for a, b in zip(tiles, tiles[1:])]),
            len(tiles))


def report_cadence(c):
    print("\n=== frames per iteration, and frames per tile ===")
    for sixty in (False, True):
        for button in ("right", "left"):
            gaps, tile_gaps, n = cadence(c, sixty, button)
            tag = "60 Hz" if sixty else "30 Hz"
            want = 1 if sixty else 2
            slipped = sum(v for k, v in gaps.items() if k != want)
            print(f"\n{tag}, walking {button}")
            print(f"  frames between iterations : {gaps}")
            print(f"  iterations over {want} frame(s) : {slipped}")
            print(f"  tiles stepped: {n}, frames between tile steps: {tile_gaps}")


# ---------------------------------------------------------------- stages


def trace(c, frames, button=None):
    events = []
    registered = []
    for name in STAGES:
        if name not in SYMS:
            continue
        bank, addr = SYMS[name]
        registered.append((bank, addr))
        c.pb.hook_register(
            bank, addr,
            (lambda n: lambda ctx: events.append((n, c.pb._cycles())))(name),
            None)
    if button:
        c.pb.button_press(button)
    c.run(frames)
    if button:
        c.pb.button_release(button)
    for bank, addr in registered:
        try:
            c.pb.hook_deregister(bank, addr)
        except Exception:
            pass
    return events


def attribute(events):
    """Split the event stream into iterations and measure the gaps."""
    iters, cur = [], None
    for name, cyc in events:
        if name == "HandleMap":
            if cur:
                iters.append(cur)
            cur = [(name, cyc)]
        elif cur is not None:
            cur.append((name, cyc))
    if cur:
        iters.append(cur)

    out = []
    for i, it in enumerate(iters[:-1]):
        marks = it + [("<next>", iters[i + 1][0][1])]
        delay = 0
        for a, b in zip(marks, marks[1:]):
            if a[0] == "NextOverworldFrame":
                delay = b[1] - a[1]
        out.append({
            "work": (marks[-1][1] - marks[0][1]) - delay,
            "gaps": [(a[0], b[1] - a[1]) for a, b in zip(marks, marks[1:])],
        })
    return out


def report_stages(c):
    print("\n=== cycles of work per iteration, by stage ===")
    print("(sampled inside hooks, so treat these as approximate; the cadence "
          "numbers above are exact)")
    for sixty in (False, True):
        set_mode(c, sixty)
        # Back up first, so the walk being measured is not spent against a
        # wall: an iteration that never steps a tile never rebuilds the map.
        c.pb.button_press("left")
        c.run(220)
        c.pb.button_release("left")
        c.run(30)
        iters = attribute(trace(c, 400, button="right"))
        budget = FRAME_CYCLES if sixty else 2 * FRAME_CYCLES
        tag = "60 Hz" if sixty else "30 Hz"
        work = sorted(x["work"] for x in iters)
        over = [x for x in iters if x["work"] > budget]
        print(f"\n{tag}, walking   budget {budget} cycles")
        print(f"  iterations {len(iters)};  work min {work[0]}  "
              f"median {work[len(work)//2]}  max {work[-1]}")
        print(f"  median is {100*work[len(work)//2]/FRAME_CYCLES:.0f}% of a "
              f"single frame")
        print(f"  over budget: {len(over)} / {len(iters)}")
        if over:
            blamed = {}
            for x in over:
                stage = max(x["gaps"], key=lambda g: g[1])[0]
                blamed[stage] = blamed.get(stage, 0) + 1
            print(f"  dominant stage on those iterations: {blamed}")
            worst = max(over, key=lambda x: x["work"])
            print(f"  worst iteration, {worst['work']} cycles "
                  f"({worst['work']/FRAME_CYCLES:.2f} frames):")
            for name, gap in worst["gaps"]:
                if gap > 2000:
                    print(f"      {name:<24} {gap:>7}  "
                          f"({gap/FRAME_CYCLES:.2f} frames)")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    with overworld() as c:
        print("map:", nav.to_new_bark_town(c))
        c.run(60)
        if what in ("cadence", "all"):
            report_cadence(c)
        if what in ("stages", "all"):
            report_stages(c)
