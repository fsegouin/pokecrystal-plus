# Pokémon Crystal+

A second-playthrough overhaul of Pokémon Crystal, built on pret's pokecrystal
and distributed as a BPS patch against the vanilla ROM.

| Feature | Toggle | Status |
|---|---|---|
| Wild encounter randomizer (tiered / untiered shuffle, or chaos) | Scientist, Elm's Lab | planned |
| Trainer roster randomizer | Scientist, Cherrygrove Pokémon Center | planned |
| Catch-up EXP booster | Scientist, Celadon Café | planned |
| Trainer and gym leader rematches | always on | planned |
| 60 fps overworld | Options, SELECT sub-page | planned |

Scripted encounters (gifts, in-game trades, statics, roamers, Bug Contest)
are never randomized. The starter is the one deliberate exception.

## Building

    make crystal          # pokecrystal.gbc (no longer matches roms.sha1 - by design)
    make patch            # patches_and_info/pokecrystal_plus_v<version>.<date>.bps

BPS rather than IPS: it stores CRC32s of both ROMs, so applying it to the wrong
file is rejected rather than silently corrupting it. The built patch and the
matching `.sym` are committed under `patches_and_info/` so the hack can be
played without a toolchain.

`pokecrystal_vanilla.gbc` is produced by `tools/build_vanilla.sh`, which builds
the pinned upstream commit in `tools/vanilla_ref.txt` in a temporary worktree
and checks it against `roms.sha1`. The ref is a commit, not a branch: Crystal+
is developed on `master`, so building `master` would diff the hack against
itself. Tests live in `tests/` (see `tests/README.md`).

## Layout

Everything new lives under a `plus` namespace so the eventual port to the
Japanese ROM is a grep away:

| Where | What |
|---|---|
| `constants/plus_constants.asm` | flag bits, mode ids |
| `data/plus/` | tier lists, trainer basics |
| `engine/plus/` | all logic |
| `docs/plus.md` | this file |
| `tests/` | PyBoy harness and per-feature checks |
| `tools/build_vanilla.sh`, `tools/make_bps.py` | vanilla reference build, patch generation |
| `patches_and_info/` | released `.bps` patches and their symbol tables |

Lines touched in vanilla files are tagged `; plus:` where a comment fits; the
hook registry below is the complete list either way.

## Storage

| Symbol | Where | Notes |
|---|---|---|
| `wPlusSeed` (2) | saved; carved from padding before `wEventFlags` | wild shuffle seed, 0 = none yet |
| `wPlusFlags` (1) | saved; same carve-out | bit 0 wild on · bits 1-2 mode · bit 3 trainers · bit 4 exp boost |
| `wPlusWildMap`, `wPlusWildInverseMap` (252 each) | WRAMX bank 2, `"Plus RAM"` | rebuilt from the seed on load; not saved |
| `FRAME_RATE_60_F` | `wOptions2` bit 1 | saved with the other options |
| ROM code and data | `"Plus"` section, bank `$7f` | ~15 KB free below the Stadium checksums |

The save layout is unchanged: new bytes replace unused padding, so vanilla
saves load with every feature off.

## Hook registry

Every place vanilla code is modified. Keep this current.

| File | Line | Feature | Change |
|---|---|---|---|
| `constants/ram_constants.asm` | `wOptions2` block | 60 fps | `FRAME_RATE_60_F` bit |
| `ram/wram.asm` | before `wEventFlags` | storage | `wPlusSeed`, `wPlusFlags` carved from `ds 100` |
| `ram/wram.asm` | new section | storage | `"Plus RAM"` |
| `layout.link` | `WRAMX 2`, `ROMX $7f` | storage | section placement |
| `main.asm` | before Stadium checksums | storage | `"Plus"` section |
| `includes.asm` | constants | storage | `plus_constants.asm` |
| `Makefile` | `.PHONY`, after `tools:` | packaging | `patch` target, vanilla ROM rule |
| `.gitignore` | end of file | packaging | venv, states, local build artifacts |

## Design notes

**Wild randomizer.** A permutation over the 150-species pool in
`data/plus/wild_tiers.asm` (everything with a wild source in vanilla, plus
Game Corner prizes and the three starters, minus the 11 legendaries and
Unown), built once from `wPlusSeed`
with Fisher-Yates and applied at encounter time. Tiered mode permutes
within the A/B/C lists in `data/plus/wild_tiers.asm`; untiered permutes the
union. Chaos mode ignores the permutation and rolls any of the 239
non-legendary, non-Unown species per encounter. The mode lives in
`wPlusFlags` bits 1-2 as a `PLUS_WILD_MODE_*` value; because those two bits can
encode four values and only three are defined, the dispatch must range-check
before indexing a jumptable - `wPlusFlags` is save-backed and therefore
attacker-controlled. Vanilla Unown slots are
never remapped, so the Ruins of Alph stay intact. The Pokédex AREA screen
applies the inverse map in shuffle modes and falls back to vanilla in chaos.

**Trainer randomizer.** `TRAINERTYPE_NORMAL` trainers only (397 of 541);
gym leaders, the rival, Elite Four and anyone with custom moves or items are
untouched. Each mon is replaced per battle by a random basic-stage species
from a level-banded list, then evolved along its own line using a level
discount: evolution thresholds are scaled by 4/3 below level 30 and 8/7 at
30 and above. Item and trade evolutions apply at 35+, happiness at 20
(babies) or 35, Tyrogue and Eevee pick a branch at random.

**Catch-up EXP.** After the Lucky Egg check, each recipient whose level is
below the fainted enemy's gets ×1.5 per started 3-level gap
(1.5^(1+⌊gap/3⌋)), clamped at 65535.

**Rematches.** `AlreadyBeatenTrainerScript` offers a rematch to every map
trainer; each gym script gets a rematch branch that skips the badge and TM.

**60 fps.** `MaxOverworldDelay` drops from 2 to 1 and `StepVectors` switches
to a table with halved deltas and doubled durations; the slow step keeps
its 1 px / 2 frame cadence by moving only on even steps. Whether the
overworld needs double-speed CPU to fit a frame is measured, not assumed.
