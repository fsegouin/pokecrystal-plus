# Pokémon Crystal+

A second-playthrough overhaul of Pokémon Crystal, built on pret's pokecrystal
and distributed as a BPS patch against the vanilla ROM.

| Feature | Toggle | Status |
|---|---|---|
| Wild encounter randomizer (tiered / untiered shuffle, or chaos) | Scientist, Elm's Lab | done |
| Trainer roster randomizer | Scientist, Cherrygrove Pokémon Center | done |
| Catch-up EXP booster | Scientist, Celadon Café | done |
| Trainer and gym leader rematches | always on | done |
| 60 fps overworld | Options, SELECT sub-page (on by default) | done |
| Running shoes (hold B) | always on | done |
| INST text speed | Options, TEXT SPEED | done |

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
| `wPlusOptionsPage` (1) | WRAM0; carved from padding before `wJumptableIndex` | which options page is showing; menu-local, never saved |
| `FRAME_RATE_60_F` | `wOptions2` bit 1 | saved with the other options; set in `data/default_options.asm`, so a new game starts at 60 fps |
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
| `maps/ElmsLab.asm` | 8, 1693 | wild | `ELMSLAB_PLUS_AIDE` object id and object event |
| `maps/ElmsLab.asm` | 165-187, 199-221, 231-253 | wild | the three poke ball scripts show and give the mapped starter |
| `maps/ElmsLab.asm` | 267, 592, 1156 | wild | `PlusOfferStarterScript`, `PlusWildAideScript`, aide text |
| `maps/ElmsLab.asm` | `ElmDirectionsText3` | wild | Elm points the player at the new aide, the one moment everyone is stood in the lab |
| `maps/ElmsLab.asm` | `PlusWildAideScript.Chaos`, `.NewPatternOnly`, `.ChaosHasNoPattern` | wild | chaos skips the pattern question, and says so if the menu asks for a reroll |
| `maps/ElmsLab.asm` | `AideText_AlwaysBusy` | wild | "only two of us" becomes three, since the lab has a third occupant now |
| `gfx/title/logo.png` | whole file | title | a `+` after CRYSTAL, the name condensed to make room |
| `maps/GoldenrodGameCorner.asm` | 183-195, 205-217, 227-239 | wild | three prize scripts name and give the mapped species |
| `maps/CeladonGameCornerPrizeRoom.asm` | 147-159, 169-181, 191-203 | wild | the same for the Kanto prizes |
| `main.asm` | `"Plus"` section | trainers | includes `data/plus/trainer_basics.asm` and `engine/plus/trainer.asm` |
| `engine/battle/read_trainer_party.asm` | `TrainerType1` loop | trainers | `farcall PlusRandomizeTrainerMon` between the species write and `predef TryAddMonToParty`, bracketed by `push hl` / `pop hl` |
| `maps/CherrygrovePokecenter1F.asm` | object list, scripts, texts, object events | trainers | Scientist at (7, 3) and its yes/no toggle script |
| `main.asm` | 690, `"Plus"` section | catch-up EXP | `INCLUDE "engine/plus/exp.asm"` |
| `engine/battle/core.asm` | 7116, `GiveExperiencePoints` | catch-up EXP | `farcall PlusCatchUpExpBoost` after the Lucky Egg boost |
| `maps/CeladonCafe.asm` | 7, 90, 218, 297 | catch-up EXP | object const, toggle script, five texts, object at (9, 1) |
| `engine/events/trainer_scripts.asm` | 4, 38 | rematches | `TalkToTrainerScript` branches to `OfferRematchScript`; shared `RematchOfferText` |
| `maps/VioletGym.asm` | 16 | rematches | `.Rematch` branch off the beaten check |
| `maps/AzaleaGym.asm` | 19 | rematches | `.Rematch` branch off the beaten check |
| `maps/GoldenrodGym.asm` | 25 | rematches | `.Rematch` branch, plus `.FightDoneTextboxOpen` re-entry |
| `maps/EcruteakGym.asm` | 28 | rematches | `.Rematch` branch off the beaten check |
| `maps/CianwoodGym.asm` | 21 | rematches | `.Rematch` branch off the beaten check |
| `maps/OlivineGym.asm` | 14 | rematches | `.Rematch` branch off the beaten check |
| `maps/MahoganyGym.asm` | 19 | rematches | `.Rematch` branch off the beaten check |
| `maps/BlackthornGym1F.asm` | 35, 66 | rematches | `.Rematch` and `.RematchAfterTM`, sharing `.StartRematch` |
| `maps/PewterGym.asm` | 15 | rematches | `.Rematch` branch off the badge check |
| `maps/CeruleanGym.asm` | 63 | rematches | `.Rematch` branch off the badge check |
| `maps/VermilionGym.asm` | 17 | rematches | `.Rematch` branch off the badge check |
| `maps/CeladonGym.asm` | 18 | rematches | `.Rematch` branch off the badge check |
| `maps/FuchsiaGym.asm` | 16 | rematches | `.Rematch` branch; faces the player and opens the textbox itself |
| `maps/SaffronGym.asm` | 18 | rematches | `.Rematch` branch off the badge check |
| `maps/SeafoamGym.asm` | 18 | rematches | `.Rematch` branch off the badge check (Blaine's gym) |
| `maps/ViridianGym.asm` | 14 | rematches | `.Rematch` branch off the badge check |
| `ram/wram.asm` | before `wJumptableIndex` | 60 fps | `wPlusOptionsPage` carved from `ds 1` |
| `ram/wram.asm` | `wOptions2` | 60 fps | comment: bit 0 is menu account, bit 1 the frame rate |
| `data/default_options.asm` | `DefaultOptions`, the `wOptions2` byte | 60 fps | `FRAME_RATE_60_F` set, so a new game starts at 60 fps |
| `engine/overworld/events.asm` | `MaxOverworldDelay` | 60 fps | `MaxOverworldDelay60`; `ResetOverworldDelay` picks between them |
| `engine/overworld/map_objects.asm` | `GetStepVector` | 60 fps | picks `StepVectors60` when the option is on |
| `engine/overworld/map_objects.asm` | after `StepVectors` | 60 fps | `StepVectors60` table |
| `engine/overworld/map_objects.asm` | `AddStepVector` | 60 fps | `CheckStepVectorHoldFrame` gate, and the routine itself |
| `engine/overworld/map_objects.asm` | `UpdateJumpPosition` | 60 fps | same gate, so a held frame does not climb the arc |
| `engine/overworld/map_objects.asm` | `_SetRandomStepDuration` | 60 fps | doubles NPC idle pauses |
| `engine/overworld/map_objects.asm` | after `AddStepVector` | 60 fps | `CheckHoldFrame60`, `SetStepDuration60`, `ScaleDuration60`, `UpdateJumpHeight60`, `CheckAlternateFrame60` |
| `engine/overworld/map_objects.asm` | `_MovementSpinRepeat`, `MovementFunction_ScreenShake` | 60 fps | durations through `SetStepDuration60` |
| `engine/overworld/map_objects.asm` | the teleport, skyfall, fishing bite, turn and skyfall top step functions | 60 fps | durations through `SetStepDuration60`, sine arcs through `UpdateJumpHeight60` |
| `engine/overworld/map_objects.asm` | `StepFunction_GotBite`, `StepFunction_RockSmash`, `StepFunction_DigTo`, `StepFunction_ScreenShake.GetSign` | 60 fps | two-state flips through `CheckAlternateFrame60` |
| `engine/overworld/movement.asm` | `Movement_step_dig`, `Movement_return_dig`, `Movement_rock_smash`, `Movement_step_wait_end`, `Movement_step_sleep_common`, `Movement_step_bump`, `Movement_tree_shake` | 60 fps | every duration written by a movement command goes through `SetStepDuration60` |
| `engine/overworld/map_object_action.asm` | after `SetFacingGrassShake` | 60 fps | `AdvanceStepFrame60` |
| `engine/overworld/map_object_action.asm` | `SetFacingStepAction`, `SetFacingSkyfall`, `SetFacingBumpAction`, `SetFacingBounce`, `SetFacingWeirdTree`, `SetFacingBoulderDust`, `SetFacingGrassShake` | 60 fps | animation counters advance through `AdvanceStepFrame60` |
| `engine/overworld/map_object_action.asm` | `CounterclockwiseSpinAction` | 60 fps | the per-facing timer doubles |
| `engine/overworld/events.asm` | after `ResetOverworldDelay` | 60 fps | `ScaleScriptDelay60` |
| `engine/overworld/scripting.asm` | `Script_deactivatefacing` | 60 fps | the turn-in-place delay doubles |
| `engine/events/map_name_sign.asm` | `InitMapNameSign`, `PlaceMapNameSign` | 60 fps | `MapNameSignFrames60` sets and re-reads the sign's countdown |
| `engine/menus/options_menu.asm` | `_Option` and below | 60 fps | SELECT sub-page: `Options_DrawPage`, `Options_FrameRate`, page-aware `GetOptionPointer` and `OptionsControl` |
| `engine/menus/options_menu.asm` | `Options_DrawPage`, after each `PlaceString` | 60 fps | `StringOptionsHintMore` and `StringOptionsHintBack` on the row the options leave empty |
| `home/double_speed.asm` | after `SwitchSpeed` | 60 fps | `PlusUpdateOverworldSpeed`, `PlusNormalSpeed`, `PlusSwitchSpeed` |
| `engine/overworld/events.asm` | `HandleMap`, `EnterMap` | 60 fps | match the CPU speed to the option |
| `engine/battle/core.asm` | `StartBattle` | 60 fps | normal speed for the battle, double again after `ExitBattle` |
| `engine/menus/save.asm` | `_SaveGameData` | 60 fps | normal speed while SRAM is written |
| `home/serial.asm` | `Serial_ExchangeByte`, `LinkTransfer`, `LinkDataReceived` | 60 fps | normal speed before an internally clocked transfer |
| `engine/link/link.asm` | `LinkCommunications` | 60 fps | the cable club writes `rSC` itself |
| `engine/printer/printer_serial.asm` | `Printer_StartTransmission` | 60 fps | normal speed for the printer |
| `engine/link/mystery_gift.asm` | `DoMysteryGift` | 60 fps | normal speed for the IR timer |
| `engine/gfx/dma_transfer.asm` | `_continue_HDMATransfer` | 60 fps | arm exactly the blocks wanted, and only stop a transfer that is still running |
| `constants/map_object_constants.asm` | `STEP_*` block | running | `STEP_RUN` at 3, shifting `STEP_LEDGE` and below up by one |
| `macros/scripts/movement.asm` | end of the command list | running | `movement_run_step_*` ($5a-$5d) and the `run_step` macro |
| `engine/overworld/movement.asm` | `MovementPointers`, after `Movement_big_step_right` | running | four `Movement_run_step_*` entries and handlers |
| `engine/overworld/map_objects.asm` | `StepVectors`, `StepVectors60` | running | a fourth row in each, copying the fast row |
| `engine/overworld/player_movement.asm` | `.walk`, `.Steps`, after `.FastStep` | running | the B test, `.run`, and the `.RunStep` command list |
| `engine/overworld/map_object_action.asm` | `SetFacingStepAction`, after `AdvanceStepFrame60` | running | `DoubleStepFrameWhenRunning` |
| `constants/ram_constants.asm` | after `TEXT_DELAY_SLOW` | INST text | `TEXT_DELAY_INST` |
| `home/print_text.asm` | `PrintLetterDelay` | INST text | a delay of zero takes the `NO_TEXT_SCROLL` exit |
| `engine/menus/options_menu.asm` | `OPT_TEXT_SPEED_*`, `Options_TextSpeed`, `GetTextSpeed` | INST text | a fourth setting at the head of the cycle |

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
giving it. The mon prize *menu* is no longer static text: `PlusBuildPrizeMenu`
in `engine/plus/prize_menu.asm` writes the row structure a ROM `MenuData` block
has into `wPlusPrizeMenuData` and the map's menu header points there, so the
rows name the shuffled species. The TM vendor's menu is untouched, and the
confirmation and hand-over lines name the mon that is actually given.

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
30 and above. Item and trade evolutions apply at 30+, happiness at 20
(babies) or 30, Tyrogue and Eevee pick a branch at random.

Rather than scale every threshold, the level is discounted once: `L - L/4`
below 30 and `L - L/8` at 30 and above give the same comparison for two
shifts and a subtract. The draw pool in `data/plus/trainer_basics.asm` is the
106 species that survive from the 117 basic-stage, non-legendary, non-Unown
list, banded by base stat total: 430 and up for level 30+, 300 to 429 for
15 to 29, below 300 for any level, with the bands falling through so a high
level draws from all three. Trade evolutions are deliberately kept, since
dropping them would cost every trainer Alakazam, Machamp, Gengar, Golem,
Steelix, Scizor and Kingdra.

The threshold started at 35 and was lowered to 30, which is worth recording:
after the 8/7 discount only 11 of the 869 mons on normal trainers reached an
effective 35, so item and trade evolutions were all but unreachable in
practice. At 30 it is 106 of them. The value is `PLUS_EVO_ITEM_LEVEL`, in one
place, if it wants moving again.

Unlike the wild randomizer the roll is unseeded: `Random` is called per mon,
so a rematch fields a different team. The species is swapped before
`TryAddMonToParty` runs, which builds the level-up moveset for whatever
species it is handed, so a randomized mon always has moves it could really
have learned at that level.

**Catch-up EXP.** After the Lucky Egg check, each recipient whose level is
below the fainted enemy's gets ×1.5 per started 3-level gap
(1.5^(1+⌊gap/3⌋)), clamped at 65535. The comparison is per recipient, read
through `wCurPartyMon`, so a participant that was back in the party rather
than on the field when the KO landed is still measured against its own level.
`BoostExp` is left alone: the clamp lives in the loop in
`engine/plus/exp.asm`, which saturates on every step, and the three vanilla
1.5x paths cannot overflow on their own (the largest possible base gain is
about 3600, and 3600 × 1.5³ is still under 16 bits).

**Rematches.** Talking to a beaten map trainer offers a rematch before the
after-battle chat; declining falls through to `AlreadyBeatenTrainerScript`, so
the vanilla line still plays. The offer hangs off `TalkToTrainerScript` rather
than off `AlreadyBeatenTrainerScript` itself because
`StartBattleWithMapTrainerScript` falls through into that label when a battle
ends: branching earlier keeps the post-battle path untouched and is what makes
a debounce unnecessary. Ordering the offer after the after-battle chat is not
possible without an engine change, because `scripttalkafter` jumps into the
trainer's after-script rather than calling it, and that script's own
`endifjustbattled` is the thing suppressing a second prompt.

Each gym leader's beaten branch gets a `.Rematch` label that offers the same
question, runs `winlosstext`, `loadtrainer`, `startbattle` and stops, so the
badge award and the TM gift are skipped. Declining falls into the vanilla
branch. Clair has two beaten branches (before the Rising Badge and after
TM24), so she gets two offers sharing one battle block. Whitney and Janine
open their textbox after the beaten check, so their branches open it
themselves.

**60 fps.** `MaxOverworldDelay` drops from 2 to 1 and `StepVectors` switches
to a table with halved deltas and doubled durations; the slow step keeps
its 1 px / 2 frame cadence by moving only on even steps. The loop needs
double-speed CPU to fit a frame; the measurements are below.

Walking is only the first of the durations the option disturbs. Almost
nothing in the overworld counts frames: it counts iterations of `HandleMap`,
and the option runs that loop twice as often, so every pause, animation and
flicker would otherwise run at double speed. Four shared helpers put that
back, all of them keyed off `FRAME_RATE_60_F`:

* `SetStepDuration60` (and the bare `ScaleDuration60` behind it) doubles a
  duration at the point it is stored, saturating at 255 rather than wrapping.
  Every write of `OBJECT_STEP_DURATION` that is not derived from an
  already-scaled value goes through it, in both `map_objects.asm` and
  `movement.asm`, and `ScaleScriptDelay60` does the same job for
  `wScriptDelay` in the other bank.
* `CheckHoldFrame60` returns carry on half of a doubled duration's
  iterations, for effects that cannot simply run longer.
  `UpdateJumpHeight60` is the one caller: the teleport and skyfall arcs index
  a sine table once per iteration for exactly 16 of them, and doubling that
  count would run the index past the end. This is the same problem the jump
  arc had, and `CheckStepVectorHoldFrame` now shares its tail.
* `CheckAlternateFrame60` reads the bit of a duration that changes once per
  30 fps frame: bit 0 normally, bit 1 once the duration is doubled. It keeps
  the two-state flickers (rock smash, dig, the fishing bob, the screen
  shake's direction) at the frequency they had, rather than doubling it along
  with the loop.
* `AdvanceStepFrame60` steps an object's animation counter. Bit 7 of
  `OBJECT_STEP_FRAME` records which half of a 30 fps frame the current
  iteration is, so the counter itself moves on every other one. Callers pass
  the wrap mask and the step, which is all that differed between the seven
  animation routines.

Three durations are deliberately left alone. The shadow, the boulder dust and
the shaking grass all derive theirs from the step duration of the object they
track, which the step table has already doubled, so they scale on their own to
within a frame or two. Emotes look like a fourth but are not: the emote object
never times out, and the pause that ends it is `Script_pause`, which counts
frames through `DelayFrames` and so is already right.

A typical iteration costs about half a frame, so the loop fits comfortably at
either rate. One iteration per tile does not: `UpdateOverworldMap` rebuilds
the on-screen tilemap from the block map every time the player steps, and the
iteration that contains it costs about 134,000 cycles, 1.9 frames. At 30 fps
the two-frame budget swallows it and the loop never slips. At normal CPU speed
and 60 fps it does not fit: that iteration takes two frames instead of one, and
a tile costs 17 frames rather than 16, with a one-frame hold at the boundary.

**Double-speed CPU.** The option therefore switches the CGB into double speed
while the overworld is running, which halves the wall clock cost of that
iteration to 0.96 frames and closes the gap: a tile is 16 frames at both rates,
and at 60 fps every one of the 16 advances the camera by a pixel. `HandleMap`
runs at exactly 1.00 iterations per frame, against 1.13 before.

`PlusUpdateOverworldSpeed` in `home/double_speed.asm` compares the wanted speed
against `rSPD` and returns without doing anything when the two already agree, so
the LCD only blanks on a real change. The overworld loop calls it once per
iteration, which costs about forty cycles when nothing has to move and means a
toggle in the options menu takes effect on the very next iteration. `EnterMap`
calls it too, before the map setup script fades the screen back in, so the one
switch a map load could need happens while the screen is already down. It is
gated on `hCGB`: `rSPD` does not exist on DMG, where a read returns $ff and
would look like double speed and drive the CPU into `stop`. The ROM is CGB only
anyway, so that gate is defensive rather than load bearing.

`PlusNormalSpeed` is the other half, and it goes in front of everything whose
timing comes from the CPU clock rather than from VBlank:

* `StartBattle`, which every battle in the game reaches, with the matching
  re-engage after `ExitBattle` while the screen is still down;
* `_SaveGameData`, the single funnel for the save menu, link saves and the hall
  of fame;
* `Serial_ExchangeByte`, `LinkTransfer` and `LinkDataReceived`, the three
  routines in `home/serial.asm` that start an internally clocked transfer, plus
  `LinkCommunications`, which writes `rSC` itself;
* `Printer_StartTransmission`, after which VBlank clocks the printer;
* `DoMysteryGift`, which drives the IR port off the timer interrupt.

The serial hooks sit in per-byte loops, so `PlusNormalSpeed` preserves every
register and fast-exits in seven instructions once the speed already matches.
`SwitchSpeed` clears `rIE` and never puts it back, so `PlusSwitchSpeed` saves
and restores it; the vanilla callers write `rIE` again themselves and these
cannot, since they run at any point in the game.

The mobile adapter needs no hook. `EnableMobile` calls `DoubleSpeed` and
`DisableMobile` calls `NormalSpeed` whatever the entry state was, and
`DisableMobile` restores `rIE` from its own backup, so the pair is already
self-consistent; `MobileAPI_SetTimer` reads `rSPD` and halves its own reload
value.

What double speed does and does not disturb, measured rather than assumed:

* **Audio** is untouched. `_UpdateSound` is called from VBlank and its only
  notion of time is a per-channel note duration decremented once per call, so
  it runs at 1.000 calls per frame in both modes. Nothing in the audio path
  uses a cycle counted delay. The APU is clocked by the base oscillator, not
  by the CPU, and the hardware moves the frame sequencer to `rDIV` bit 13 in
  double speed so envelopes and sweeps keep their rate.
* **The timer interrupt** doubles, from 16 Hz to 32 Hz, and nothing reads it.
  `rTAC` is started at 4096 Hz in `home/init.asm` with `rTMA` zero, so `rTIMA`
  overflows every 256 ticks; the vector at $0050 goes to `MobileTimer`, which
  returns immediately unless `hMobile` is set. Mystery Gift is the one other
  timer user and it is switched back to normal speed first.
* **The RTC** is unaffected. It lives in the MBC3 cartridge on its own crystal.
  `LatchClock` writes 0 then 1 to `rRTCLATCH`, which is edge triggered with no
  timing requirement, and `GetClock` then reads the registers through `rRAMB`.
  Nothing in that path counts CPU cycles.
* **Serial** would be affected, since the internal clock divides the CPU clock,
  which is exactly why every internally clocked transfer is behind a switch
  back to normal speed.
* `rDIV` also runs twice as fast, which shifts what `Random` returns for a
  given input. It does not make the sequence any less random.

**The HBlank DMA terminate.** One vanilla routine was not safe to run twice as
fast, and it is the one every menu and textbox goes through:
`_continue_HDMATransfer` in `engine/gfx/dma_transfer.asm`, reached from
`OpenText`, `CloseText`, `ReanchorMap`, `StartMenu` and every `Get1bppViaHDMA`
or `Get2bppViaHDMA` font load.

It arms an HBlank DMA for one more 16 byte block than it wants, waits for the
right number of scanlines, and then clears bit 7 of `rVDMA_LEN` to stop the
last one. That write only means "stop" while a transfer is running. Once a
transfer has finished the register reads `$ff`, and clearing bit 7 of `$ff`
writes `$7f`, which is not a stop at all: it is a request for a fresh general
purpose DMA of `($7f + 1) * 16` = 2048 bytes, from wherever the finished
transfer left its source and destination pointers. That splatters 2 KB over
VRAM, which is why opening the START menu or talking to an NPC turned the
overworld tileset at `vTiles2` into stripes while the tilemap underneath it
stayed perfectly correct.

The routine therefore depended on the transfer *not* being finished when it
got there, with a margin of exactly one block. The fix removes the dependency
rather than widening the margin: arm exactly the number of blocks wanted, so
the transfer stops itself, and guard the write with `bit 7, [hl]` so it only
ever runs against a transfer that is genuinely still going. The number of
blocks actually transferred is unchanged at either speed, and the 30 fps
screen is byte for byte what it was before.

Worth recording for whoever hits this next: the trigger observed here is an
emulator inaccuracy. PyBoy moves 16 bytes per 206 CPU cycles with a
`# TODO: adjust for double speed` next to it, so at double speed its HBlank
DMA runs two blocks per HBlank instead of one and finishes early. Real CGB
hardware does one block per HBlank at either speed, so the vanilla code very
likely survives on hardware. The guard is worth having anyway: a write whose
meaning flips from "abort" to "start a 2 KB DMA" depending on a one block race
is not something to leave standing under a feature that changes the CPU clock.
(The technique of running the whole overworld at double speed, and the fact
that this file is where it bites, was confirmed against an existing
double-speed Crystal engine.)

**What was tried and rejected.** Adaptive pacing, where `NextOverworldFrame`
skips its `DelayFrame` when a VBlank already passed during the iteration's
work, does nothing here. It was built and measured: the skip fires on exactly
the iterations that overrun, once per tile, and a tile still takes 17 frames
with the same hold at the boundary. Skipping the delay stops the loop adding a
frame on top of the overrun, but it cannot recover the wall clock time the
overrunning iteration already spent, so the 15 cheap iterations plus one that
costs 1.9 frames still add up to about 17. Making the stall go away without
double speed would mean making `UpdateOverworldMap` itself cheaper, by
splitting the tilemap rebuild across two iterations, which is a much larger
change to a routine the whole overworld depends on.

**Running shoes.** Holding B while walking on foot covers a tile in 8 frames
instead of 16, in both frame rate modes. Nothing gates it: there is no item to
find, no badge to earn and no option to set, so it is on from the first step
out of the bedroom.

`STEP_RUN` sits at 3, the value vanilla leaves free. The low nybble of an
object's `OBJECT_WALKING` is two bits of step type and two of direction, so
`GetStepVector` has room for exactly four rows and vanilla fills three of them.
Putting `STEP_RUN` last leaves `STEP_SLOW`, `STEP_WALK` and `STEP_BIKE` on the
rows they already had, so no existing movement command changes meaning; the
constants below it (`STEP_LEDGE` through `STEP_WALK_IN_PLACE`) shift up by one,
which is free because they are only ever arguments to
`DoPlayerMovement.DoStep` and never name a row.

The bike is not touched. Both bike rows are the vanilla bytes and the new
running rows copy them, so a run and a bike ride cover a tile in the same
time. Matching the bike rather than beating it was the deliberate choice: the
alternative, doubling the bike to keep a hierarchy, would have put it at two
frames a tile, eight pixels of scroll per frame, faster than anything vanilla
ever moves, and would have changed the feel of every bike route and of Cycling
Road to buy a distinction the bike does not actually need. The bike still has
reasons to exist that are not speed: the routes that require it, the
downhill and uphill handling in `wBikeFlags`, and the places running is allowed
and it is not (every interior in the game).

The run needs its own row rather than an alias of the bike's precisely because
the two must stay distinguishable: the bike has its own player state, sprite
and music, and a run must inherit none of them.

`SetFacingStepAction` advances an animation counter once per overworld
iteration and takes two bits of it as the sprite frame, so a step that covers a
tile in half the iterations would show half as many frames of leg movement per
tile and the player would appear to skate. `DoubleStepFrameWhenRunning` doubles
the counter's step while `OBJECT_WALKING` holds the running row, which is the
same trick in the other direction from `AdvanceStepFrame60`, and the two
compose: at 60 fps the counter is doubled and then held on every other
iteration. A walking tile advances the counter 8 and a running tile 7, because
the single iteration between two steps, where `OBJECT_WALKING` reads
`STANDING`, cannot tell a run from a walk and advances by one either way. The
legs therefore cycle at 7/8 of the walking rate rather than exactly matching
it, which is not visible; what would have been visible is the 1/2 the tier
gets without the doubling. The bike keeps its vanilla one sprite frame per
tile, since a bike sprite has no legs to get wrong.

Trainer spotting needs nothing. `CheckTrainerBattle` runs from `PlayerEvents`,
which the overworld loop only reaches while `wMapEventStatus` is `MAPEVENTS_ON`,
and a step turns it off until `PLAYERSTEP_STOP_F` is set again. So sight is
checked once per completed tile step, not once per frame: `tests/test_running.py`
measures exactly one check per tile walking, running and biking, at both frame
rates. Running crosses a trainer's line of sight in half the wall clock time
but gets the same number of chances to be caught, so it cannot be used to slip
past a trainer. Other running shoe implementations add a routine that snaps
spinning trainers to face a running player; that is a difficulty change rather
than a fix, and it would make the gym spinner puzzles strictly harder than
vanilla, so it is deliberately left out.

B is free in the overworld. `CheckMenuOW` binds only START and SELECT, and
`CheckAPressOW` only A; nothing else reads `PAD_B` outside a menu or a text
box, and none of those run while the player is stepping. `OWPlayerInput` calls
`PlayerMovement` first and returns as soon as a step is taken, so a held B
cannot reach a button action mid-step, and while the player stands still B is
read by nothing at all: it still cancels menus and advances text as it always
did.

Only the on-foot branch of `.TryStep` looks at B. Surfing goes through
`.TrySurf` and the bike and skateboard through `.BikeCheck` before that branch
is reached; ice, ledges, bumps, warps and the tiles that force a direction all
return earlier still. `tests/test_running.py` drives `DoPlayerMovement` directly
for each of those and checks the movement command it picks is the same with B
held as without.

**INST text speed.** A fourth value in the `wOptions` text delay field, shown
as `INST`, which prints a whole box with no per-character delay. It does not
skip or auto-advance anything: A still moves box to box exactly as before.

The field is a frame count (`TEXT_DELAY_FAST` is 1, `MED` 3, `SLOW` 5), so
`TEXT_DELAY_INST` is the honest value for it: zero. Nothing else in the saved
options byte moves, the three vanilla values keep the encoding they always had,
and a save from any earlier build (or from vanilla Crystal) reads back
unchanged.

Zero is not quite enough on its own. Storing it in `wTextDelayFrames` would
already exit the wait loop immediately, but `PrintLetterDelay` checks the
joypad first and spends a frame on any letter printed while A or B is held,
which is an acceleration from MED and SLOW and would be a deceleration from
INST. So INST returns at the top of the routine instead, on the same `ret`
`NO_TEXT_SCROLL` uses. That path is not invented for this: it is what every
menu in the game already sets `NO_TEXT_SCROLL` to reach, so the behaviour is
one vanilla routines have exercised since 2000. The box is written into the
tilemap in a single pass and VBlank pushes it whole on the next frame.

Home is very nearly full: the routine had four spare bytes in ROM0 before this,
and the check is written as `and TEXT_DELAY_MASK` / `ret z` rather than a `cp`
so that it costs three of them. An `assert` pins the constant to zero, since
that is what makes the `ret z` correct.

`INST` goes at the head of `OPT_TEXT_SPEED_*` rather than the tail, so LEFT
still means faster and RIGHT slower and the cycle reads INST, FAST, MID, SLOW.
Nothing else reads the field expecting three values: the only other writers are
`SaveOptions` (which touches bit 4 alone), the catch tutorial and the link
cable, and both of those force MED. Values the field cannot legitimately hold
(2, 4, 6, 7) still display as MID, exactly as in vanilla.


**The empty menu box frame, and why it is still there.** Pressing START shows
the menu box about ten frames before the items land in it. This is vanilla
behaviour, measured against a clean build of the pinned upstream commit: box at
frame 19, text at frame 30 at 30 fps, and 14 and 24 at 60 fps. It was
investigated and deliberately left alone. The accounting is here so nobody has
to do it twice.

What the menu waits for is not the tilemap transfer.
`ReanchorBGMap_NoOAMUpdate` leaves the window covering the whole screen with a
frozen copy of the overworld in `vBGMap1`, blacks out `vBGMap0` and re-anchors
it. The frame the menu appears in is the one where `hWY` goes back to $90 and
uncovers `vBGMap0`, and that write sits inside `LoadFonts_NoOAMUpdate`, after
`LoadFontsExtra` but before `LoadStandardFont`. So the box is uncovered before
the font its items are drawn in exists in VRAM, and the items only arrive when
`.GetInput` reaches `SetUpMenu` and `ApplyTilemap`.

Reordering `StartMenu` to load the standard font, write the item text and
transfer the tilemap before that `hWY` write does put the box and the items on
screen in the same frame, with no empty box at all. It was written and
measured: one change of 10880 pixels and no later text change, at both frame
rates, with the settled menu pixel for pixel identical to vanilla's. The
trouble is where the frames go. The reveal moves from 19 to 28 at 30 fps and
from 14 to 22 at 60 fps, because it now waits for the font; the complete menu
arrives two frames sooner than the text used to, but the first nine frames
after the START press show nothing at all. That is a worse press to hold in the
hand, so it is not in the build.

The font load is what costs those nine frames, and it is worth knowing that the
cost is not VRAM bandwidth. `_LoadStandardFont` is four `Get1bppViaHDMA` calls
of 32 tiles, and `HDMATransfer1bpp` splits each into 16-tile chunks with a
`call DelayFrame` in front of every one: eight frames of pacing for eight
HBlank transfers that occupy about 16 scanlines each. `wScratchTilemap` is
1 KiB, so the expanded 2bpp of 64 tiles would fit in it and the chunk could be
four times larger, but that routine is behind every 1bpp graphics load in the
game and is not worth disturbing for a menu.

Keeping the menu font resident so it never has to be loaded is not possible.
The VRAM accounting, on CGB, in tiles:

| Bank 0 | | Bank 1 | |
|---|---|---|---|
| `vTiles0` $8000 | OBJ tiles $00-$7f | `vTiles3` $8000 | overworld sprite standing frames; pics, battle transition, fishing |
| `vTiles1` $8800 | OBJ tiles $80-$ff, **and** BG $80-$ff: the overworld font *or* the standard font | `vTiles4` $8800 | overworld sprite walking frames |
| `vTiles2` $9000 | BG $00-$7f: map tileset $00-$5f, frame and font extras $60-$7f | `vTiles5` $9000 | map tileset $00-$5f; $60-$7f mostly free |

`vTiles1` is one 128-tile slot and the two fonts are both exactly 128 tiles, so
they cannot both be resident: `LoadOverworldFont` (from `CloseText`) and
`LoadStandardFont` (from `LoadFonts_NoOAMUpdate`) overwrite each other by
design. There is no free 128-tile region to move either of them to. `vTiles4`
looks free until `GetUsedSprite` is read closely: `.CopyToVram` picks `rVBK` 1
for every sprite whose tile index is below $80, so the overworld's sprite
graphics live in `vTiles3` and `vTiles4`, not in bank 0. Only `vTiles5`
$60-$7f is spare, which is 32 tiles.

Even with room, a BG tile is only fetched from bank 1 when the attribute byte
for that cell says so, and `PlaceString` writes the tilemap alone: the attrmap
under text is set per box by `TextboxPalette` and per screen by everything
else. Moving the font to bank 1 would mean setting a bank bit on every cell of
every text-bearing screen in the game, and providing bank 1 copies of every
non-font tile that shares those cells (the box frame, the cursor, HP bars, item
icons). That is a rewrite of the graphics model, not a menu fix.
