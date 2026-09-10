"""Scripted navigation from the bedroom to New Bark Town.

Everything the frame-rate checks need to see (a scrolling camera, NPCs with
their own movement, a slow_step cutscene) is outdoors, so the checks have to
walk there from a fresh game. Coordinates come from maps/PlayersHouse2F.asm,
maps/PlayersHouse1F.asm and maps/NewBarkTown.asm.
"""

NEW_BARK_TOWN = (24, 4)
PLAYERS_HOUSE_1F = (24, 6)
PLAYERS_HOUSE_2F = (24, 7)


def where(c):
    return c.read("wMapGroup"), c.read("wMapNumber")


def coords(c):
    return c.read("wYCoord"), c.read("wXCoord")


def step(c, button, n=1, hold=20, settle=24):
    for _ in range(n):
        c.pb.button_press(button)
        c.run(hold)
        c.pb.button_release(button)
        c.run(settle)


def clear_script(c, button="A", limit=150):
    """Advance whatever script is running until control comes back.

    wScriptRunning is 0 exactly when no script owns the loop. A advances text
    and answers YES; B advances text and answers NO. Mom's daylight-saving
    prompt loops on NO, so her speech needs A, while an accidental NPC
    conversation is best dismissed with B so it cannot start another one.
    """
    for _ in range(limit):
        if not c.read("wScriptRunning"):
            c.run(20)
            if not c.read("wScriptRunning"):
                return True
        c.press(button, hold=6, release=6)
        c.run(24)
    return False


def to_new_bark_town(c):
    step(c, "down", 2)
    step(c, "right", 5)
    step(c, "up", 4)            # stairs, warp to PlayersHouse1F (1, 9)
    c.run(60)
    assert where(c) == PLAYERS_HOUSE_1F, where(c)
    step(c, "down", 3)
    clear_script(c)             # Mom's PokeGear / clock speech
    walk_to(c, 7, 6)            # the tile above the front door
    step(c, "down", 1)          # warp to New Bark Town
    c.run(120)
    clear_script(c, button="B")
    step(c, "down", 2)          # clear of the doorway, room to walk in both axes
    step(c, "left", 2)
    clear_script(c, button="B")
    return where(c)


def walk_to(c, y, x, limit=24):
    """Nudge toward (y, x) one tile at a time. Indoor rooms only: there is no
    pathfinding here, just axis-at-a-time movement past open floor."""
    for _ in range(limit):
        cy, cx = coords(c)
        if (cy, cx) == (y, x):
            return True
        if cx != x:
            step(c, "right" if cx < x else "left")
        elif cy != y:
            step(c, "down" if cy < y else "up")
        if coords(c) == (cy, cx):   # blocked, try the other axis
            if cy != y:
                step(c, "down" if cy < y else "up")
            elif cx != x:
                step(c, "right" if cx < x else "left")
    return coords(c) == (y, x)
