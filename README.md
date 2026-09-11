# Pokémon Crystal+ [![Build Status][ci-badge]][ci]

A second-playthrough overhaul of Pokémon Crystal, built on
[pret's pokecrystal disassembly][pret] and distributed as a BPS patch against
the vanilla ROM.

## Features

| Feature | Toggle |
|---|---|
| Wild encounter randomizer (tiered / untiered shuffle, or chaos) | Scientist, Elm's Lab |
| Trainer roster randomizer | Scientist, Cherrygrove Pokémon Center |
| Catch-up EXP booster | Scientist, Celadon Café |
| Trainer and gym leader rematches | always on |
| Shiny chain for wild and static encounters | always on, POKé RADAR turns it off |
| POKé RADAR key item to check, clear or turn off the chain | Elm's aide |
| $1 repels in every general mart, topped off when one wears off until you go indoors | always on |
| Vanilla bug fixes: catch rate, battle engine, AI, HP bar, five-digit EXP | always on |
| Low HP alarm beeps four times, then stops | always on |
| Type matchup markers on the battle move list (▲ ▼ ×) | always on |
| B on the battle menu moves the cursor to RUN | always on |
| 60 fps overworld | Options, SELECT sub-page (on by default) |
| Running shoes (hold B) | always on |
| INST text speed | Options, TEXT SPEED |
| One-line battle HUD | always on |

The three Scientist features start off on a new game, and vanilla saves load
with all three off. Scripted encounters (gifts, in-game trades, statics,
roamers, Bug Contest) are never randomized; the starter is the one exception.

The full design notes, storage layout and the list of every vanilla hook are in
[docs/plus.md](docs/plus.md).

## Playing

Released patches are in [patches_and_info/](patches_and_info/), alongside the
symbol table for the latest one. The current release is v0.1.0.

Apply the `.bps` to an unmodified Pokémon Crystal (UE) ROM with Flips, beat or
any BPS patcher. The patch stores CRC32s of both ROMs, so applying it to the
wrong file is rejected rather than silently producing a broken ROM.

## Building

Set up the toolchain as described in [INSTALL.md](INSTALL.md), then:

    make crystal            # pokecrystal.gbc
    make patch              # patches_and_info/pokecrystal_plus_v<version>.<yymmdd>.bps

`pokecrystal.gbc` no longer matches `roms.sha1`, by design. When
`pokecrystal_vanilla.gbc` is missing or `tools/vanilla_ref.txt` has changed,
`make patch` first runs `tools/build_vanilla.sh`, which builds that pinned
upstream commit in a temporary worktree, checks it against `roms.sha1`, and
saves it as `pokecrystal_vanilla.gbc` to diff against.
Patching needs Python 3 and nothing else.

## Tests

PyBoy-driven checks for each feature live in [tests/](tests/README.md). They
are not part of `make`.

## Credits

Built on [pokecrystal][pret] by [pret](https://pret.github.io/). For questions
about the disassembly itself, see its [FAQ](FAQ.md),
[documentation][docs], [wiki][wiki] and [symbols][symbols].

Crystal+ takes inspiration from:

- [Shin Pokémon Red/Blue][shin] by jojobear13
- [Crystal Clear][cc] by ShockSlayer
- [CrystalShireEngine][cse], whose 60 fps overworld the one here is based on

[pret]: https://github.com/pret/pokecrystal
[docs]: https://pret.github.io/pokecrystal/
[wiki]: https://github.com/pret/pokecrystal/wiki
[symbols]: https://github.com/pret/pokecrystal/tree/symbols
[shin]: https://github.com/jojobear13/shinpokered
[cc]: https://github.com/ShockSlayer/ccdocs
[cse]: https://github.com/8bitZeta/CrystalShireEngine
[ci]: https://github.com/fsegouin/pokecrystal-plus/actions
[ci-badge]: https://github.com/fsegouin/pokecrystal-plus/actions/workflows/main.yml/badge.svg
