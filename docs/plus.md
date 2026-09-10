# Pokémon Crystal+

A second-playthrough overhaul of Pokémon Crystal, built on pret's pokecrystal
and distributed as a BPS patch against the vanilla ROM.

| Feature | Toggle | Status |
|---|---|---|
| Wild encounter randomizer (tiered / untiered shuffle, or chaos) | Scientist, Elm's Lab | done |
| Trainer roster randomizer | Scientist, Cherrygrove Pokémon Center | done |

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
| `wPlusRandState` (2), `wPlusStarterSlots` (3), `wPlusMappedSpecies` (1) | WRAMX bank 2, `"Plus RAM"` | build scratch and script hand-off; not saved |
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
| `data/events/special_pointers.asm` | end of table | wild | seven `Plus*` specials |
| `engine/overworld/wildmons.asm` | 32-37 | wild | `FindNest` wraps its scan in the inverse map |
| `engine/overworld/wildmons.asm` | 326-329 | wild | `ChooseWildEncounter` maps the species it just read |
| `engine/events/overworld.asm` | 1474-1476 | wild | `.goodtofish` maps the species `Fish` returned |
| `engine/events/treemons.asm` | 187-191 | wild | `SelectTreeMon` maps the species before storing it |
| `engine/menus/intro_menu.asm` | 65 | wild | `NewGame` calls `PlusInitNewGame` after `ResetWRAM` |
| `engine/menus/save.asm` | 610, 628 | wild | both `TryLoadSaveFile` paths rebuild the maps |
| `maps/ElmsLab.asm` | 8, 1649 | wild | `ELMSLAB_PLUS_AIDE` object id and object event |
| `maps/ElmsLab.asm` | 165-187, 199-221, 231-253 | wild | the three poke ball scripts show and give the mapped starter |
| `maps/ElmsLab.asm` | 267, 592, 1121 | wild | `PlusOfferStarterScript`, `PlusWildAideScript`, aide text |
| `maps/GoldenrodGameCorner.asm` | 183-195, 205-217, 227-239 | wild | three prize scripts name and give the mapped species |
| `maps/CeladonGameCornerPrizeRoom.asm` | 147-159, 169-181, 191-203 | wild | the same for the Kanto prizes |
| `main.asm` | `"Plus"` section | trainers | includes `data/plus/trainer_basics.asm` and `engine/plus/trainer.asm` |
| `engine/battle/read_trainer_party.asm` | `TrainerType1` loop | trainers | `farcall PlusRandomizeTrainerMon` between the species write and `predef TryAddMonToParty`, bracketed by `push hl` / `pop hl` |
| `maps/CherrygrovePokecenter1F.asm` | object list, scripts, texts, object events | trainers | Scientist at (7, 3) and its yes/no toggle script |

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

The permutation is rebuilt from the seed rather than saved, which makes
determinism a hard requirement: `PlusBuildWildMaps` never calls `Random`, only
a 16-bit xorshift seeded from `wPlusSeed`. `wPlusWildInverseMap` doubles as the
Fisher-Yates scratch buffer while the forward map is being built, and is filled
in for real afterwards.

Every hook reaches the randomizer through `farcall`, which can carry neither an
argument nor a result in `a`: the macro loads `a` with a bank number going in,
and `ReturnFarCall` leaves `a` holding `c` coming back. `PlusMapWildSpecies`
therefore takes the species in `b` and returns it in `b`. The one place the
vanilla value of `a` still matters is `ChooseWildEncounter`, where the level in
`a` is what the vanilla validation bug actually checks; the hook pushes and pops
it around the call so that bug behaves exactly as it always did.

`ClearWRAM` only clears WRAM bank 1 (a vanilla bug), so bank 2 holds garbage at
boot. Nothing reads it: `wPlusFlags` lives in bank 1 and is therefore zero until
either a new game or a save load, and both rebuild the maps before the flag can
be set.

`givepoke` only takes a literal species, so the starter and Game Corner prize
scripts call `PlusGiveScriptMon` instead, with the level and held item written
through `loadmem`. The species handed over comes from `wPlusMappedSpecies`
rather than `wScriptVar`, so the yes/no prompt and the dex check in between are
free to use `wScriptVar` and chaos mode cannot re-roll between naming a mon and
giving it. The Game Corner *menu* labels are static text and still read ABRA,
CUBONE and so on; the vendor's confirmation and hand-over lines name the mon
that is actually given.

The starters use their own selection over `PlusTierStarter` alone, seeded from
`wPlusSeed`, so the three balls hold three distinct starter-legal mon and the
offer does not move while the player looks at all three. The rival still reads
`EVENT_GOT_*_FROM_ELM`, which the ball scripts set unchanged, so his choice
follows the ball taken rather than the species.

**Trainer randomizer.** `TRAINERTYPE_NORMAL` trainers only (397 of 541);
gym leaders, the rival, Elite Four and anyone with custom moves or items are
untouched. Each mon is replaced per battle by a random basic-stage species
from a level-banded list, then evolved along its own line using a level
discount: evolution thresholds are scaled by 4/3 below level 30 and 8/7 at
30 and above. Item and trade evolutions apply at 35+, happiness at 20
(babies) or 35, Tyrogue and Eevee pick a branch at random.

Rather than scale every threshold, the level is discounted once: `L - L/4`
below 30 and `L - L/8` at 30 and above give the same comparison for two
shifts and a subtract. The draw pool in `data/plus/trainer_basics.asm` is the
106 species that survive from the 117 basic-stage, non-legendary, non-Unown
list, banded by base stat total: 430 and up for level 30+, 300 to 429 for
15 to 29, below 300 for any level, with the bands falling through so a high
level draws from all three. Trade evolutions are deliberately kept, since
dropping them would cost every trainer Alakazam, Machamp, Gengar, Golem,
Steelix, Scizor and Kingdra.

One consequence of the 35 threshold is worth knowing: the highest-level
`TRAINERTYPE_NORMAL` mon in the game is Cooltrainer Quinn's level 38 pair,
and 38 discounts to an effective 34. So no stone or trade evolution can
actually reach the field until rematches raise trainer levels past 40. The
threshold is `PLUS_EVO_ITEM_LEVEL`, in one place, if that turns out to be a
disappointment rather than a slow burn.

Unlike the wild randomizer the roll is unseeded: `Random` is called per mon,
so a rematch fields a different team. The species is swapped before
`TryAddMonToParty` runs, which builds the level-up moveset for whatever
species it is handed, so a randomized mon always has moves it could really
have learned at that level.

