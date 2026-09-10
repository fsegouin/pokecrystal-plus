#!/usr/bin/env python3
"""Generate gfx/font/font_half.png, the font the battle HUD name row uses.

Only the NAME is condensed, to five pixels a character, because only the name
is too wide to share a row with the gender symbol and the level. Everything
else on the row keeps the game's own graphics at their own size and is copied
in here at build time: the gender symbols, the ":L" and the level digits, plus
the nine letters the status strings are spelled from.

Every glyph sits on rows 1 to 7 of its cell. The standard font puts letters on
rows 0 to 6 and the gender symbols on 0 to 7, so drawn as they come the symbol
hangs a pixel below whatever is beside it. Dropping everything a row and
fitting the symbols into seven puts the whole row on one baseline.

Edit the art below and re-run. The PNG is the committed asset; rgbgfx turns it
into tiles at build time.
"""
import os

GLYPH_W, H = 5, 8
CELL_W = 8   # glyphs sit in ordinary 8x8 cells, left aligned, so rgbgfx
             # produces a normal 1bpp font and the renderer only has to shift
TOP = 1      # every glyph starts here, so they all share a baseline at row 7

G = {}


def g(ch, *rows):
    """Define a narrow glyph. Art is at most seven rows, drawn from TOP."""
    assert len(rows) <= H - TOP, (ch, len(rows))
    art = ["....."] * TOP + list(rows)
    art += ["....."] * (H - len(art))
    for r in art:
        assert len(r) == GLYPH_W, (ch, r)
    G[ch] = art


# --- uppercase -------------------------------------------------------------
g('A', ".##..", "#..#.", "#..#.", "####.", "#..#.", "#..#.", "#..#.")
g('B', "###..", "#..#.", "###..", "#..#.", "#..#.", "#..#.", "###..")
g('C', ".###.", "#....", "#....", "#....", "#....", "#....", ".###.")
g('D', "###..", "#..#.", "#..#.", "#..#.", "#..#.", "#..#.", "###..")
g('E', "####.", "#....", "###..", "#....", "#....", "#....", "####.")
g('F', "####.", "#....", "###..", "#....", "#....", "#....", "#....")
g('G', ".###.", "#....", "#....", "#.##.", "#..#.", "#..#.", ".###.")
g('H', "#..#.", "#..#.", "####.", "#..#.", "#..#.", "#..#.", "#..#.")
g('I', "###..", ".#...", ".#...", ".#...", ".#...", ".#...", "###..")
g('J', "..##.", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##..")
g('K', "#..#.", "#.#..", "##...", "##...", "#.#..", "#.#..", "#..#.")
g('L', "#....", "#....", "#....", "#....", "#....", "#....", "####.")
g('M', "#..#.", "####.", "####.", "#..#.", "#..#.", "#..#.", "#..#.")
g('N', "#..#.", "##.#.", "##.#.", "#.##.", "#.##.", "#..#.", "#..#.")
g('O', ".##..", "#..#.", "#..#.", "#..#.", "#..#.", "#..#.", ".##..")
g('P', "###..", "#..#.", "#..#.", "###..", "#....", "#....", "#....")
g('Q', ".##..", "#..#.", "#..#.", "#..#.", "#.##.", "#..#.", ".###.")
g('R', "###..", "#..#.", "#..#.", "###..", "#.#..", "#..#.", "#..#.")
g('S', ".###.", "#....", "#....", ".##..", "...#.", "...#.", "###..")
g('T', "####.", ".#...", ".#...", ".#...", ".#...", ".#...", ".#...")
g('U', "#..#.", "#..#.", "#..#.", "#..#.", "#..#.", "#..#.", ".##..")
g('V', "#..#.", "#..#.", "#..#.", "#..#.", "#..#.", ".##..", ".##..")
g('W', "#..#.", "#..#.", "#..#.", "#..#.", "####.", "####.", "#..#.")
g('X', "#..#.", "#..#.", ".##..", ".##..", ".##..", "#..#.", "#..#.")
g('Y', "#..#.", "#..#.", "#..#.", ".##..", "..#..", "..#..", "..#..")
g('Z', "####.", "...#.", "..#..", ".#...", "#....", "#....", "####.")

# --- lowercase -------------------------------------------------------------
# the five with tails put their body a row higher, so the tail has somewhere
# to go without pushing the glyph off the bottom of the cell
g('a', ".....", ".....", ".##..", "...#.", ".###.", "#..#.", ".###.")
g('b', "#....", "#....", "###..", "#..#.", "#..#.", "#..#.", "###..")
g('c', ".....", ".....", ".###.", "#....", "#....", "#....", ".###.")
g('d', "...#.", "...#.", ".###.", "#..#.", "#..#.", "#..#.", ".###.")
g('e', ".....", ".....", ".##..", "#..#.", "####.", "#....", ".###.")
g('f', "..##.", ".#...", "###..", ".#...", ".#...", ".#...", ".#...")
g('g', ".....", ".###.", "#..#.", "#..#.", ".###.", "...#.", ".##..")
g('h', "#....", "#....", "###..", "#..#.", "#..#.", "#..#.", "#..#.")
g('i', ".#...", ".....", "##...", ".#...", ".#...", ".#...", "###..")
g('j', "...#.", ".....", "..##.", "...#.", "...#.", "#..#.", ".##..")
g('k', "#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#.")
g('l', "##...", ".#...", ".#...", ".#...", ".#...", ".#...", "###..")
g('m', ".....", ".....", "###..", "#.#..", "#.#..", "#.#..", "#.#..")
g('n', ".....", ".....", "###..", "#..#.", "#..#.", "#..#.", "#..#.")
g('o', ".....", ".....", ".##..", "#..#.", "#..#.", "#..#.", ".##..")
g('p', ".....", "###..", "#..#.", "#..#.", "###..", "#....", "#....")
g('q', ".....", ".###.", "#..#.", "#..#.", ".###.", "...#.", "...#.")
g('r', ".....", ".....", "#.##.", "##...", "#....", "#....", "#....")
g('s', ".....", ".....", ".###.", "#....", ".##..", "...#.", "###..")
g('t', ".#...", ".#...", "###..", ".#...", ".#...", ".#...", "..##.")
g('u', ".....", ".....", "#..#.", "#..#.", "#..#.", "#..#.", ".###.")
g('v', ".....", ".....", "#..#.", "#..#.", "#..#.", ".##..", ".##..")
g('w', ".....", ".....", "#.#..", "#.#..", "#.#..", "#.#..", "###..")
g('x', ".....", ".....", "#..#.", ".##..", ".##..", ".##..", "#..#.")
g('y', ".....", "#..#.", "#..#.", "#..#.", ".###.", "...#.", ".##..")
g('z', ".....", ".....", "####.", "..#..", ".#...", "#....", "####.")

# --- digits ----------------------------------------------------------------
g('0', ".##..", "#..#.", "#.##.", "##.#.", "#..#.", "#..#.", ".##..")
g('1', "..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###.")
g('2', ".##..", "#..#.", "...#.", "..#..", ".#...", "#....", "####.")
g('3', "###..", "...#.", "...#.", ".##..", "...#.", "...#.", "###..")
g('4', "..##.", ".#.#.", "#..#.", "####.", "...#.", "...#.", "...#.")
g('5', "####.", "#....", "###..", "...#.", "...#.", "#..#.", ".##..")
g('6', ".###.", "#....", "###..", "#..#.", "#..#.", "#..#.", ".##..")
g('7', "####.", "...#.", "..#..", "..#..", ".#...", ".#...", ".#...")
g('8', ".##..", "#..#.", "#..#.", ".##..", "#..#.", "#..#.", ".##..")
g('9', ".##..", "#..#.", "#..#.", ".###.", "...#.", "...#.", ".##..")

# --- punctuation -----------------------------------------------------------
g(' ')
g(':', ".....", ".#...", ".#...", ".....", ".#...", ".#...", ".....")
g('.', ".....", ".....", ".....", ".....", ".....", ".....", ".#...")
g(',', ".....", ".....", ".....", ".....", ".....", ".#...", ".##..")
g('-', ".....", ".....", ".....", "###..", ".....", ".....", ".....")
g("'", ".#...", ".#...", ".....", ".....", ".....", ".....", ".....")
g('!', ".#...", ".#...", ".#...", ".#...", ".#...", ".....", ".#...")
g('?', ".##..", "#..#.", "...#.", "..#..", ".#...", ".....", ".#...")
g('/', "...#.", "...#.", "..#..", "..#..", ".#...", ".#...", "#....")
g('%', "#..#.", "...#.", "..#..", ".#...", "#....", "#..#.", ".....")

# Narrow glyphs first, then the wide ones. The renderer keys off the index:
# anything from WIDE_FIRST on advances eight pixels instead of five.
NARROW = (
    [chr(c) for c in range(ord('A'), ord('Z') + 1)]
    + [chr(c) for c in range(ord('a'), ord('z') + 1)]
    + [chr(c) for c in range(ord('0'), ord('9') + 1)]
    + [' ', ':', '.', ',', '-', "'", '!', '?', '/', '%']
)
# male, female, ":L", then the ten digits. All but the gender symbols are
# lifted from the originals.
WIDE = ['\x01', '\x02', '\x03'] + [f'\\d{d}' for d in range(10)]

# A status shows as a tag rather than three letters: white on a black rounded
# bar, the way later generations badge them. Nothing in the palette changes.
# Every battle background palette runs white to black, so a tile with its
# background filled and the letters knocked out of it comes out white on black
# for free. Each tag is three cells, the same width a level takes, so the row
# is laid out identically either way.
STATUSES = ("SLP", "PSN", "BRN", "FRZ", "PAR")
TAG_W = 3 * 8
WIDE += [f'\\t{name}{i}' for name in STATUSES for i in range(3)]
WIDE_FIRST = len(NARROW)
ORDER = NARROW + WIDE
for _ch in WIDE:
    G[_ch] = ["........"] * H

# The gender symbols are eight rows tall in the standard font, where every
# letter is seven, so copying them straight in leaves them hanging a pixel
# below whatever sits beside them. These are the same two shapes fitted into
# seven rows: the arrow keeps its point and its barbs and the circle below it
# loses a row, and the female circle keeps its shape and the cross loses a row
# of stem. Both then sit on the same baseline as everything else.
MALE_ART = ["...#....",
            "..###...",
            ".#.#.#..",
            "#..#..#.",
            "..###...",
            ".#...#..",
            "..###..."]
FEMALE_ART = ["..###...",
              ".#...#..",
              ".#...#..",
              "..###...",
              ".#####..",
              "...#....",
              "...#...."]

# Four by five, so three of them and a gap fit inside a tag with a margin.
TAG_LETTERS = {
    'S': (".###", "#...", ".##.", "...#", "###."),
    'L': ("#...", "#...", "#...", "#...", "####"),
    'P': ("###.", "#..#", "###.", "#...", "#..."),
    'N': ("#..#", "##.#", "#.##", "#..#", "#..#"),
    'B': ("###.", "#..#", "###.", "#..#", "###."),
    'R': ("###.", "#..#", "###.", "#.#.", "#..#"),
    'F': ("####", "#...", "###.", "#...", "#..."),
    'Z': ("####", "...#", ".##.", "#...", "####"),
    'A': (".##.", "#..#", "####", "#..#", "#..#"),
}


def tag_bitmap(name):
    """A rounded black bar with the three letters knocked out of it."""
    on = [[False] * TAG_W for _ in range(H)]
    for y in range(H):
        for x in range(TAG_W):
            # clip the four corners to round the ends
            corner = min(x, TAG_W - 1 - x) + min(y, H - 1 - y)
            on[y][x] = corner >= 1
    width = 3 * 4 + 2 * 1                  # three letters and two gaps
    ox = (TAG_W - width) // 2
    # Five rows of letter in an eight row bar cannot sit dead centre. One row
    # of bar above and two below reads better than the other way round.
    oy = 1
    for i, ch in enumerate(name):
        art = TAG_LETTERS[ch]
        for y, row in enumerate(art):
            for x, cell in enumerate(row):
                if cell == "#":
                    on[y + oy][ox + i * 5 + x] = False
    return on


MALE, FEMALE = 0xEF, 0xF5


def copy_originals(px, cols):
    """Take the wide glyphs from the game's own graphics, dropped to TOP."""
    from PIL import Image
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def cell(ch):
        i = ORDER.index(ch)
        return (i % cols) * CELL_W, (i // cols) * H

    def blit(ch, spx, tile, per_row):
        sx, sy = (tile % per_row) * 8, (tile // per_row) * 8
        ox, oy = cell(ch)
        for y in range(H):
            for x in range(8):
                src_y = y - TOP
                on = 0 <= src_y < 8 and spx[sx + x, sy + src_y] < 128
                px[ox + x, oy + y] = 0 if on else 255

    def draw(ch, art):
        ox, oy = cell(ch)
        for y in range(H):
            for x in range(8):
                row = y - TOP
                on = 0 <= row < len(art) and art[row][x] == "#"
                px[ox + x, oy + y] = 0 if on else 255

    draw('\x01', MALE_ART)
    draw('\x02', FEMALE_ART)

    for name in STATUSES:
        bits = tag_bitmap(name)
        for third in range(3):
            ox, oy = cell(f'\\t{name}{third}')
            for y in range(H):
                for x in range(8):
                    px[ox + x, oy + y] = 0 if bits[y][third * 8 + x] else 255

    font = Image.open(os.path.join(root, "gfx", "font", "font.png")).convert("L")
    fpx = font.load()
    for d in range(10):
        blit(f'\\d{d}', fpx, (0xF6 + d) - 0x80, 16)

    # ":L" is not in the standard font; it is the third tile of the enemy HP
    # bar border, loaded at BG tile $6e.
    lv = Image.open(os.path.join(root, "gfx", "battle",
                                 "enemy_hp_bar_border.png")).convert("L")
    blit('\x03', lv.load(), 0x6E - 0x6C, 4)


def main():
    from PIL import Image
    cols = 16
    rows = (len(ORDER) + cols - 1) // cols
    im = Image.new('L', (cols * CELL_W, rows * H), 255)
    px = im.load()
    for i, ch in enumerate(ORDER):
        art = G[ch]
        ox, oy = (i % cols) * CELL_W, (i // cols) * H
        for y in range(H):
            for x in range(GLYPH_W):
                if art[y][x] == '#':
                    px[ox + x, oy + y] = 0
    copy_originals(px, cols)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, 'gfx', 'font', 'font_half.png')
    im.save(out)
    print(f"wrote {out}  {im.size[0]}x{im.size[1]}  "
          f"{len(NARROW)} narrow + {len(WIDE)} wide glyphs "
          f"(WIDE_FIRST = {WIDE_FIRST})")


if __name__ == '__main__':
    main()
