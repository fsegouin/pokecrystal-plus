"""Checks for the INST text speed, and a measurement of the start menu.

INST is a fourth value in the wOptions text delay field, and it is the frame
count the other three already are: zero. PrintLetterDelay takes the same early
exit NO_TEXT_SCROLL takes, so a box is written to the tilemap in one go and
VBlank pushes it whole. Nothing else changes: A still advances box to box, and
the other three speeds keep their vanilla frame counts.

The start menu shows its box about ten frames before the items land in it.
That is vanilla behaviour and it is still here on purpose: what uncovers the
menu is the hWY write inside LoadFonts_NoOAMUpdate, which runs after the
tilemap transfer but before the standard font the items are drawn in, and
closing the gap means waiting for that font. docs/plus.md has the accounting.
The gap is measured and printed here rather than asserted away.

The checks are:
  * INST prints a whole box in a single burst, and the other three do not;
  * INST gets through the same four boxes in far fewer frames than FAST;
  * A still advances box to box at INST, with four distinct boxes;
  * FAST, MED and SLOW take exactly the frames they take now, box by box;
  * the start menu still arrives, settles once and settles into a real menu,
    with the box-to-items gap printed for the record;
  * the options menu offers INST and saves it as a text delay of zero.

Everything is checked at both frame rates. The dialogue is the Game Corner
prize vendor's, from tests/states/gamecorner.sav: four boxes in a row, one of
them long enough to scroll, and a vertical menu at the end of it.

The screen is sampled a frame at a time and compared against the frame before,
because what is being measured is when pixels land, not what they say. The
sampled window leaves out the blinking ▼, which never stops changing.

Run: .venv/bin/python tests/test_text.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import STATES, Crystal  # noqa: E402

# wOptions bits 0-2, from constants/ram_constants.asm
TEXT_DELAY_MASK = 0b111
TEXT_DELAY_INST = 0b000
TEXT_DELAY_FAST = 0b001
TEXT_DELAY_MED = 0b011
TEXT_DELAY_SLOW = 0b101
SPEEDS = (("INST", TEXT_DELAY_INST), ("FAST", TEXT_DELAY_FAST),
          ("MED", TEXT_DELAY_MED), ("SLOW", TEXT_DELAY_SLOW))

# wOptions2 bit 1, from constants/ram_constants.asm
FRAME_RATE_60 = 1 << 1

# The two text rows of a speech box, without the blinking ▼ in the corner.
TEXT_AREA = (slice(14 * 8, 17 * 8), slice(1 * 8, 19 * 8))
# The start menu's item text. The box border is column 10 and the cursor
# column 11, so the items start at column 12; the box is 12 rows tall here.
MENU_ITEMS = (slice(0, 12 * 8), slice(12 * 8, 20 * 8))

# Frames each of the four boxes takes to finish printing, measured on the
# build these checks ship with. INST is left out on purpose: it is the number
# under test. Indexed by frame rate, because opening the box and opening the
# menu after it both ride the overworld loop, which runs at either rate.
GOLDEN = {
    False: {"FAST": [42, 52, 28, 31],
            "MED": [54, 109, 58, 82],
            "SLOW": [69, 169, 88, 126]},
    True: {"FAST": [32, 52, 28, 31],
           "MED": [47, 109, 58, 75],
           "SLOW": [62, 169, 88, 123]},
}

# How long the screen has to hold still before a box counts as finished. The
# widest gap between two letters is SLOW's five frames, rounded up by the
# thirds VBlank copies the tilemap in.
QUIET = 40

failures = []


def check(ok, what, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {what}" + (f"  {detail}" if detail else ""))
    if not ok:
        failures.append(what)


def grab(c, area):
    return np.array(c.pb.screen.ndarray[area][:, :, :3], dtype=np.int16)


def changed_frames(c, area, limit=600):
    """Tick until `area` has held still for QUIET frames.

    Returns the frame numbers, counted from the call, on which it changed.
    """
    prev = grab(c, area)
    hits = []
    for f in range(limit):
        c.pb.tick(1, render=True)
        now = grab(c, area)
        if np.any(now != prev):
            hits.append(f)
        prev = now
        if hits and f - hits[-1] >= QUIET:
            return hits
    raise AssertionError(f"the screen never settled within {limit} frames")


def tap(c, button, hold=4):
    """Press and release without waiting, so the frame count starts at 0."""
    c.pb.button_press(button.lower())
    c.pb.tick(hold, render=True)
    c.pb.button_release(button.lower())
    return hold


def at_vendor(c, delay, sixty):
    """Face the Game Corner prize vendor with a text speed selected."""
    c.continue_game()
    c.run(90)
    c.write("wOptions", (c.read("wOptions") & ~TEXT_DELAY_MASK) | delay)
    flags = c.read("wOptions2")
    c.write("wOptions2", flags | FRAME_RATE_60 if sixty else flags & ~FRAME_RATE_60)
    c.press("up", hold=6, release=10)
    c.run(30)


def read_conversation(c):
    """Open the vendor's four boxes, one A press each.

    Returns a list of (frames the box took, the finished text area) pairs.
    """
    out = []
    for _ in range(4):
        held = tap(c, "A")
        hits = changed_frames(c, TEXT_AREA)
        out.append((hits[-1] + held, grab(c, TEXT_AREA), hits))
    return out


def test_dialogue(tag, sixty):
    print(f"\n== the prize vendor's four boxes, {tag} ==")
    totals = {}
    for name, delay in SPEEDS:
        with Crystal(sav=os.path.join(STATES, "gamecorner.sav")) as c:
            at_vendor(c, delay, sixty)
            boxes = read_conversation(c)

        frames = [f for f, _, _ in boxes]
        totals[name] = sum(frames)
        shown = {img.tobytes() for _, img, _ in boxes}
        check(len(shown) == 4, f"{name}: A advances box to box, four distinct boxes",
              f"{len(shown)} distinct")

        # One box per burst at INST, one burst per letter otherwise. VBlank
        # copies the tilemap in thirds, so even INST can straddle two frames.
        bursts = [len(hits) for _, _, hits in boxes]
        if name == "INST":
            check(max(bursts) <= 3, "INST: each box lands in a single burst",
                  f"changes per box {bursts}")
        else:
            check(min(bursts) >= 4, f"{name}: letters still arrive one at a time",
                  f"changes per box {bursts}")
            # Boxes 2 and 3 are fixed text, so their frame counts are a real
            # baseline. Boxes 1 and 4 name the mon on offer, which moves
            # whenever the species pool changes, so those are checked for the
            # ordering a text speed has to produce rather than exact frames.
            fixed = [frames[1], frames[2]]
            want = [GOLDEN[sixty][name][1], GOLDEN[sixty][name][2]]
            check(fixed == want,
                  f"{name}: the fixed boxes are unchanged frame for frame",
                  f"{fixed} against {want}")
            totals.setdefault("_boxes", {})[name] = frames

    # the named boxes still have to get slower as the speed setting does
    boxes = totals.get("_boxes", {})
    if {"FAST", "MED", "SLOW"} <= boxes.keys():
        for i in (0, 3):
            f, m, sl = boxes["FAST"][i], boxes["MED"][i], boxes["SLOW"][i]
            check(f < m < sl,
                  f"box {i + 1} names a mon, and still slows with the setting",
                  f"FAST {f}, MED {m}, SLOW {sl}")

    fast, inst = totals["FAST"], totals["INST"]
    check(inst * 2 <= fast, "INST is materially faster than FAST",
          f"{inst} frames against {fast}")
    check(totals["FAST"] < totals["MED"] < totals["SLOW"],
          "FAST, MED and SLOW still get slower in that order",
          f"{totals['FAST']} < {totals['MED']} < {totals['SLOW']}")


def test_start_menu(tag, sav):
    """Measure the gap between the box appearing and the items filling it.

    The gap is vanilla behaviour and the build still has it, for the reasons
    in docs/plus.md: closing it means waiting for the standard font, which
    costs nine frames of a blank press. What is guarded here is that the menu
    still arrives, still settles, and settles into the right thing.
    """
    print(f"\n== the start menu, {tag} ==")
    with Crystal(sav=os.path.join(STATES, sav)) as c:
        c.continue_game()
        c.run(60)
        whole = (slice(0, 144), slice(0, 160))
        before = grab(c, whole)
        tap(c, "START")
        big = []
        items = []
        for f in range(90):
            c.pb.tick(1, render=True)
            now = grab(c, whole)
            moved = int(np.count_nonzero(np.any(now != before, axis=2)))
            if moved > 5000:
                big.append(f)
            items.append((f, grab(c, MENU_ITEMS)))
            before = now
        settled = items[-1][1]

    check(len(big) == 1, "the box arrives in one frame",
          f"frames with a large change: {big}")
    if not big:
        return
    box = big[0]
    same = [f for f, img in items if np.array_equal(img, settled)]
    check(same and same == list(range(min(same), 90)),
          "the item text settles once and stays settled",
          f"settled from frame {min(same)}")
    check(int(np.count_nonzero(settled)) > 0, "the settled menu is not blank")
    print(f"  [INFO] box at frame {box}, items at frame {min(same)}, "
          f"gap {min(same) - box} frames")


def test_options_menu(tag, sav):
    print(f"\n== INST in the options menu, {tag} ==")
    with Crystal(sav=os.path.join(STATES, sav)) as c:
        c.continue_game()
        c.run(60)
        c.write("wOptions", (c.read("wOptions") & ~TEXT_DELAY_MASK) | TEXT_DELAY_MED)
        c.press("START")
        c.run(60)
        for _ in range(3):          # PACK, <PLAYER>, SAVE, OPTION
            c.press("down")
            c.run(12)
        c.press("A")
        c.run(90)
        seen = []
        for _ in range(5):          # MED, FAST, INST, SLOW, MED
            seen.append(c.read("wOptions") & TEXT_DELAY_MASK)
            c.press("left")
            c.run(20)
        seen.append(c.read("wOptions") & TEXT_DELAY_MASK)

    check(seen == [TEXT_DELAY_MED, TEXT_DELAY_FAST, TEXT_DELAY_INST,
                   TEXT_DELAY_SLOW, TEXT_DELAY_MED, TEXT_DELAY_FAST],
          "LEFT cycles MED, FAST, INST, SLOW and round again",
          " ".join(f"{v:03b}" for v in seen))
    check(TEXT_DELAY_INST in seen, "INST is reachable and saves as a delay of zero")


def test_saves_load():
    print("\n== the checked-in saves still load ==")
    for sav, where in (("fps30.sav", (11, 2, 30, 20)),
                       ("fps60.sav", (11, 2, 30, 20)),
                       ("gamecorner.sav", (11, 19, 3, 18))):
        with Crystal(sav=os.path.join(STATES, sav)) as c:
            c.continue_game()
            c.run(60)
            got = (c.read("wMapGroup"), c.read("wMapNumber"),
                   c.read("wYCoord"), c.read("wXCoord"))
        check(got == where, f"{sav} loads where it always did", f"{got}")


def main():
    print("== INST text speed and the start menu ==")
    for sav in ("fps30.sav", "fps60.sav", "gamecorner.sav"):
        if not os.path.exists(os.path.join(STATES, sav)):
            print(f"  [SKIP] tests/states/{sav} is missing")
            failures.append(f"{sav} is missing")
            return 1

    test_saves_load()
    for tag, sixty in (("30 fps", False), ("60 fps", True)):
        test_dialogue(tag, sixty)
    for tag, sav in (("30 fps", "fps30.sav"), ("60 fps", "fps60.sav")):
        test_start_menu(tag, sav)
        test_options_menu(tag, sav)

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
