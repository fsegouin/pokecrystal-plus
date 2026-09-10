; Wild encounter randomizer.
;
; wPlusWildMap is a permutation of the species ids that appear in the wild
; tables. Encounter code hands a vanilla species to PlusMapWildSpecies and
; gets the replacement back; the level and the slot it came from are left
; alone, so a Route 29 slot stays a Route 29 slot at its Route 29 level.
;
; The permutation is rebuilt from wPlusSeed rather than saved, so nothing
; new has to fit into the save file. That makes determinism a requirement:
; nothing in the build path may call Random, or a loaded game would drift
; away from the one that was saved. PlusRandomByte is the only source of
; randomness used while building, and it is seeded from wPlusSeed alone.
;
; See docs/plus.md for the storage map and the hook registry.


PlusBuildWildMaps::
; Rebuild wPlusWildMap and wPlusWildInverseMap from wPlusSeed and wPlusFlags.
	ldh a, [rWBK]
	push af

	ld a, BANK(wPlusSeed)
	ldh [rWBK], a
	ld a, [wPlusSeed]
	ld b, a
	ld a, [wPlusSeed + 1]
	or b
	jr nz, .have_seed
	; A save written before the randomizer existed has no pattern to
	; rebuild, so leave the maps alone and keep every feature off.
	xor a
	ld [wPlusFlags], a

.have_seed
	ld a, BANK(wPlusWildMap)
	ldh [rWBK], a
	; ClearWRAM only wipes bank 1, and a reset partway through a gift would
	; leave an allowance behind, so start the count at zero on every load.
	xor a
	ld [wPlusShinyRolls], a
	call .SetIdentity

	call PlusGetWildMode
	jr nc, .done

	cp PLUS_WILD_MODE_TIERED
	jr z, .tiered
	cp PLUS_WILD_MODE_UNTIERED
	jr z, .untiered
	; Chaos rolls per encounter and has no permutation. An out of range
	; mode can only come from a tampered save, and gets the same
	; treatment: the identity map, which is vanilla behaviour.
	jr .done

.tiered
	call PlusSeedRandom
	ld hl, PlusTierC
	call .ShuffleTier
	ld hl, PlusTierB
	call .ShuffleTier
	ld hl, PlusTierA
	call .ShuffleTier
	jr .invert

.untiered
	call PlusSeedRandom
	call .ShuffleAllTiers

.invert
	call .BuildInverse

.done
	pop af
	ldh [rWBK], a
	ret

.SetIdentity:
; Every species maps to itself, which is what vanilla does.
	ld hl, wPlusWildMap
	ld de, wPlusWildInverseMap
	ld c, NUM_POKEMON + 1
	xor a
.identity_loop
	ld [hli], a
	ld [de], a
	inc de
	inc a
	dec c
	jr nz, .identity_loop
	ret

.ShuffleTier:
; Shuffle the -1 terminated species list at hl among itself.
	push hl
	ld de, wPlusWildInverseMap
	ld c, 0
	call .AppendToScratch
	call PlusShuffleBuffer
	pop hl
	ld de, wPlusWildInverseMap
	; fallthrough

.ApplyScratch:
; Record the shuffled run at de as the destinations of the list at hl.
	ld a, [hli]
	cp -1
	ret z
	push hl
	ld c, a
	ld b, 0
	ld hl, wPlusWildMap
	add hl, bc
	ld a, [de]
	inc de
	ld [hl], a
	pop hl
	jr .ApplyScratch

.ShuffleAllTiers:
; Treat all three tiers as one list, so anything can land anywhere.
	ld de, wPlusWildInverseMap
	ld c, 0
	ld hl, PlusTierC
	call .AppendToScratch
	ld hl, PlusTierB
	call .AppendToScratch
	ld hl, PlusTierA
	call .AppendToScratch
	call PlusShuffleBuffer
	ld de, wPlusWildInverseMap
	ld hl, PlusTierC
	call .ApplyScratch
	ld hl, PlusTierB
	call .ApplyScratch
	ld hl, PlusTierA
	jr .ApplyScratch

.AppendToScratch:
; Copy the -1 terminated list at hl to de, advancing de and counting into c.
	ld a, [hli]
	cp -1
	ret z
	ld [de], a
	inc de
	inc c
	jr .AppendToScratch

.BuildInverse:
; wPlusWildInverseMap answers "which vanilla species became this one",
; which is what the Pokedex AREA screen needs.
	xor a
	ld [wPlusWildInverseMap], a
	ld c, 1
.inverse_loop
	ld b, 0
	ld hl, wPlusWildMap
	add hl, bc
	ld a, [hl]
	ld e, a
	ld d, 0
	ld hl, wPlusWildInverseMap
	add hl, de
	ld a, c
	ld [hl], a
	inc c
	ld a, c
	cp NUM_POKEMON + 1
	jr c, .inverse_loop
	ret


PlusShuffleBuffer:
; Fisher-Yates over the c bytes at wPlusWildInverseMap.
; WRAM bank 2 must be selected. Clobbers everything.
	ld a, c
	cp 2
	ret c
	dec a
	ld b, a
.loop
	ld a, b
	inc a
	ld c, a
	push bc
	call PlusRandomRange
	pop bc
	ld hl, wPlusWildInverseMap
	ld e, a
	ld d, 0
	add hl, de
	push hl
	ld hl, wPlusWildInverseMap
	ld e, b
	ld d, 0
	add hl, de
	pop de
	ld a, [de]
	ld c, a
	ld a, [hl]
	ld [de], a
	ld a, c
	ld [hl], a
	dec b
	jr nz, .loop
	ret


PlusSeedRandom:
; Reset the deterministic RNG to wPlusSeed.
; WRAM bank 2 must be selected on entry, and is selected again on return.
; Clobbers bc.
	ld a, BANK(wPlusSeed)
	ldh [rWBK], a
	ld a, [wPlusSeed]
	ld b, a
	ld a, [wPlusSeed + 1]
	ld c, a
	ld a, BANK(wPlusRandState)
	ldh [rWBK], a
	ld a, b
	ld [wPlusRandState], a
	ld a, c
	ld [wPlusRandState + 1], a
	ret


PlusRandomRange:
; Return a value from 0 to c - 1 in a, drawn from the seeded RNG.
; The rejection loop matches RandomRange, so the spread is the same, but
; the numbers come from wPlusSeed instead of the divider register.
; WRAM bank 2 must be selected. Preserves bc; clobbers de and hl.
	push bc
	; b = $100 % c
	xor a
	sub c
.mod
	sub c
	jr nc, .mod
	add c
	ld b, a
.loop
	call PlusRandomByte
	ld e, a
	add b
	jr c, .loop
	ld a, e
	call SimpleDivide
	pop bc
	ret


PlusRandomByte:
; Step the seeded RNG and return a byte in a.
; A 16-bit xorshift with the (7, 9, 8) triple: full period over every
; nonzero state, and cheap enough to run a few hundred times on a map load.
; WRAM bank 2 must be selected. Clobbers de and hl.
	ld a, [wPlusRandState]
	ld l, a
	ld a, [wPlusRandState + 1]
	ld h, a

	; hl ^= hl << 7
	ld d, h
	ld e, l
rept 7
	add hl, hl
endr
	ld a, h
	xor d
	ld h, a
	ld a, l
	xor e
	ld l, a

	; hl ^= hl >> 9, which only ever touches the low byte
	ld a, h
	srl a
	xor l
	ld l, a

	; hl ^= hl << 8, which only ever touches the high byte
	ld a, l
	xor h
	ld h, a

	ld a, l
	ld [wPlusRandState], a
	ld a, h
	ld [wPlusRandState + 1], a
	ret


PlusMapWildSpecies::
; Map the vanilla wild species in b to the randomized one, returned in b.
; Preserves c, de and hl.
;
; Both the argument and the result travel in b because every caller reaches
; this through farcall, which loads a with a bank number on the way in and
; leaves a holding c on the way out. Only bc, de and hl survive the trip.
;
; Empty slots and Unown are never remapped: Unown has to stay in the Ruins
; of Alph for the puzzles, the printer and its own dex page to make sense.
	push hl
	push de
	push bc
	call .Map
	pop bc
	pop de
	pop hl
	ld b, a
	ret

.Map:
	ld a, b
	and a
	ret z
	cp UNOWN
	ret z
	call PlusGetWildMode
	jr c, .on
	ld a, b
	ret

.on
	cp PLUS_WILD_MODE_CHAOS
	jr z, .chaos
	cp PLUS_WILD_MODE_TIERED
	jr z, .lookup
	cp PLUS_WILD_MODE_UNTIERED
	jr z, .lookup
	ld a, b
	ret

.lookup
	ldh a, [rWBK]
	ld c, a
	ld a, BANK(wPlusWildMap)
	ldh [rWBK], a
	ld hl, wPlusWildMap
	ld e, b
	ld d, 0
	add hl, de
	ld b, [hl]
	ld a, c
	ldh [rWBK], a
	ld a, b
	ret

.chaos
	ld a, NUM_POKEMON
	call RandomRange
	inc a
	ld c, a
	ld hl, PlusChaosBans
.banned_loop
	ld a, [hli]
	cp -1
	jr z, .rolled
	cp c
	jr nz, .banned_loop
	jr .chaos

.rolled
	ld a, c
	ret


PlusMapStarterSpecies:
; Map the vanilla starter in a to the one on offer this run, returned in a.
; Anything that is not one of the three starters is returned untouched.
; Preserves nothing.
	ld b, a
	ld c, PLUS_STARTER_LEFT
	cp CYNDAQUIL
	jr z, .got_slot
	ld c, PLUS_STARTER_MIDDLE
	cp TOTODILE
	jr z, .got_slot
	ld c, PLUS_STARTER_RIGHT
	cp CHIKORITA
	jr z, .got_slot
	ld a, b
	ret

.got_slot
	call PlusGetWildMode
	jr c, .on
	ld a, b
	ret

.on
	ldh a, [rWBK]
	push af
	ld a, BANK(wPlusStarterSlots)
	ldh [rWBK], a
	push bc
	call PlusComputeStarterSlots
	pop bc
	ld b, 0
	ld hl, wPlusStarterSlots
	add hl, bc
	ld c, [hl]
	ld b, 0
	ld hl, PlusTierStarter
	add hl, bc
	ld c, [hl]
	pop af
	ldh [rWBK], a
	ld a, c
	ret


PlusComputeStarterSlots:
; Pick three distinct PlusTierStarter entries from wPlusSeed and leave
; their indices in wPlusStarterSlots.
;
; The picks are derived, not stored, so looking at one ball and backing out
; cannot shuffle the other two. Each draw is taken over a range one shorter
; than the last and then stepped past the picks already made, which keeps
; the three distinct without a retry loop that a bad seed could stall in.
; WRAM bank 2 must be selected. Clobbers everything.
	call PlusSeedRandom
	call .CountStarters

	call PlusRandomRange
	ld [wPlusStarterSlots + 0], a

	dec c
	call PlusRandomRange
	ld hl, wPlusStarterSlots
	cp [hl]
	jr c, .got_second
	inc a
.got_second
	ld [wPlusStarterSlots + 1], a

	dec c
	call PlusRandomRange
	ld b, a
	; d and e take the first two picks in order
	ld a, [wPlusStarterSlots + 0]
	ld d, a
	ld a, [wPlusStarterSlots + 1]
	ld e, a
	cp d
	jr nc, .sorted
	ld a, d
	ld d, e
	ld e, a
.sorted
	ld a, b
	cp d
	jr c, .stepped_past_first
	inc a
.stepped_past_first
	cp e
	jr c, .stepped_past_second
	inc a
.stepped_past_second
	ld [wPlusStarterSlots + 2], a
	ret

.CountStarters:
; Return the PlusTierStarter length in c.
	ld hl, PlusTierStarter
	ld c, 0
.count_loop
	ld a, [hli]
	cp -1
	ret z
	inc c
	jr .count_loop


PlusInitNewGame::
; Start a new game with every feature off and a fresh pattern waiting, so
; the aide in Elm's lab has something to turn on.
	xor a
	call PlusWriteFlags
	call PlusChainReset
	; fallthrough

PlusGenerateSeed::
; Roll a new pattern and rebuild the maps around it.
	call PlusNewSeed
	jp PlusBuildWildMaps


PlusNewSeed:
; Store a new nonzero seed in wPlusSeed.
; The hardware RNG alone would give the same pattern to everyone who starts
; a game at the same point in the intro, so the clock is mixed in too.
	call Random
	ldh a, [hRandomAdd]
	ld d, a
	ldh a, [hRTCSeconds]
	xor d
	ld d, a
	call Random
	ldh a, [hRandomSub]
	ld e, a
	ldh a, [hRTCMinutes]
	xor e
	ld e, a
	ldh a, [hRTCDayLo]
	xor d
	ld d, a

	; a zero seed means "no pattern", so never hand one out
	ld a, d
	or e
	jr nz, .nonzero
	ld de, 1
.nonzero

	ldh a, [rWBK]
	push af
	ld a, BANK(wPlusSeed)
	ldh [rWBK], a
	ld a, e
	ld [wPlusSeed], a
	ld a, d
	ld [wPlusSeed + 1], a
	pop af
	ldh [rWBK], a
	ret


PlusGetWildMode:
; Return the wild randomizer mode in a with carry set, or a = 0 with carry
; clear when the randomizer is off. Preserves bc, de and hl.
	call PlusReadFlags
	bit PLUS_WILD_ENABLED_F, a
	jr z, .off
	and PLUS_WILD_MODE_MASK
rept PLUS_WILD_MODE_SHIFT
	srl a
endr
	scf
	ret

.off
	xor a
	ret


PlusReadFlags:
; Return wPlusFlags in a whatever WRAM bank is selected.
; Preserves bc, de and hl.
	push bc
	ldh a, [rWBK]
	ld b, a
	ld a, BANK(wPlusFlags)
	ldh [rWBK], a
	ld a, [wPlusFlags]
	ld c, a
	ld a, b
	ldh [rWBK], a
	ld a, c
	pop bc
	ret


PlusWriteFlags:
; Store a in wPlusFlags whatever WRAM bank is selected.
; Preserves bc, de and hl.
	push bc
	ld c, a
	ldh a, [rWBK]
	ld b, a
	ld a, BANK(wPlusFlags)
	ldh [rWBK], a
	ld a, c
	ld [wPlusFlags], a
	ld a, b
	ldh [rWBK], a
	pop bc
	ret


PlusUnmapNestSpecies::
; The Pokedex AREA screen scans the vanilla encounter tables, so ask it
; about whatever now turns into the species the player is looking at.
	ld hl, wPlusWildInverseMap
	jr PlusRemapNestSpecies

PlusMapNestSpecies::
; Put the species the AREA screen was asked about back where it found it.
	ld hl, wPlusWildMap
	; fallthrough

PlusRemapNestSpecies:
; Replace wNamedObjectIndex with its entry in the map at hl.
; Preserves bc, de and hl.
	push bc
	push de
	push hl
	call PlusGetWildMode
	jr nc, .done
	; Chaos has no permutation to undo, so AREA falls back to vanilla.
	cp PLUS_WILD_MODE_CHAOS
	jr z, .done
	ld a, [wNamedObjectIndex]
	and a
	jr z, .done
	cp UNOWN
	jr z, .done
	ld e, a
	ld d, 0
	add hl, de
	ldh a, [rWBK]
	ld b, a
	ld a, BANK(wPlusWildMap)
	ldh [rWBK], a
	ld a, [hl]
	ld c, a
	ld a, b
	ldh [rWBK], a
	ld a, c
	ld [wNamedObjectIndex], a

.done
	pop hl
	pop de
	pop bc
	ret


; Specials. Map scripts cannot reach any of the above directly, and givepoke
; only takes a literal species, so the prize, starter and aide scripts go
; through these.

PlusMapPrizeMon::
; wScriptVar holds a Game Corner prize species on the way in, and the
; species actually on offer on the way out.
	ld a, [wScriptVar]
	ld b, a
	call PlusMapWildSpecies
	ld a, b
	jr PlusStashMappedMon

PlusMapStarterMon::
; wScriptVar holds one of the three starters on the way in, and the one in
; that poke ball this run on the way out.
	ld a, [wScriptVar]
	call PlusMapStarterSpecies
	; fallthrough

PlusStashMappedMon:
; Remember the species in a, so a script can name it now and hand it over
; after a yes/no prompt has overwritten wScriptVar.
	ld [wScriptVar], a
	ld b, a
	ldh a, [rWBK]
	ld c, a
	ld a, BANK(wPlusMappedSpecies)
	ldh [rWBK], a
	ld a, b
	ld [wPlusMappedSpecies], a
	ld a, c
	ldh [rWBK], a
	ret

PlusRecallMappedMon::
; wScriptVar = the species the last map or starter special settled on.
	ldh a, [rWBK]
	ld c, a
	ld a, BANK(wPlusMappedSpecies)
	ldh [rWBK], a
	ld a, [wPlusMappedSpecies]
	ld b, a
	ld a, c
	ldh [rWBK], a
	ld a, b
	ld [wScriptVar], a
	ret

PlusGiveScriptMon::
; Give the species the last map special settled on, at wCurPartyLevel and
; holding wCurItem. Stands in for givepoke, which can only name a species
; literally. Reading the stash rather than wScriptVar means the dex check
; in between is free to use wScriptVar for its own purposes.
	call PlusRecallMappedMon
	ld [wCurPartySpecies], a

	; A mon the game hands you is one you keep, so make it worth looking at.
	; The allowance is a plain count of DV rolls, which is what a chain would
	; raise too if one is ever added.
	ld a, PLUS_SHINY_ROLLS_SCRIPT
	call PlusSetShinyRolls

	ld b, 0 ; not another trainer's mon
	farcall GivePoke
	push bc
	xor a
	call PlusSetShinyRolls
	pop bc
	ld a, b
	ld [wScriptVar], a
	ret

PlusSetShinyRolls:
; a = how many times the next mon generated should roll its DVs.
	ld b, a
	ldh a, [rWBK]
	push af
	ld a, BANK(wPlusShinyRolls)
	ldh [rWBK], a
	ld a, b
	ld [wPlusShinyRolls], a
	pop af
	ldh [rWBK], a
	ret

; ============================================================================
; The shiny chain
;
; Beat or catch the same species over and over and its DVs get re-rolled more
; times per encounter, which is the only thing shininess in this generation
; responds to. Beating a different species starts the count again on that one.
;
; Only a defeat or a catch moves the count. Fleeing, being fled from and
; whiting out all leave it alone: nothing died, so nothing changed.
;
; The state is three bytes of SRAM, written as the battle ends rather than
; when the player saves. A one-off encounter can therefore be chained by
; beating it and resetting without saving: the overworld rolls back to the
; last save and the chain does not.
; ============================================================================

PlusChainLoad:
; Reads the chain into de: d = species, e = count. Both come back zero when
; SRAM has never held a chain, so a fresh cartridge reads as no chain rather
; than as whatever those bytes happened to be.
;
; Leaves SRAM open on the chain's bank; every caller closes it.
	ld a, BANK(sPlusChainCheck)
	call OpenSRAM
	ld a, [sPlusChainCheck]
	cp PLUS_CHAIN_MAGIC
	jr nz, .blank
	; One byte of magic is not proof: a cartridge that has never held a chain
	; lands on it once in 256, and GetPokemonName indexes its list without a
	; bound, so a species past the end would print ten tiles of ROM as a name.
	ld a, [sPlusChainSpecies]
	cp NUM_POKEMON + 1
	jr nc, .blank
	ld d, a
	ld a, [sPlusChainCount]
	ld e, a
	ret

.blank
	ld de, 0
	ret

PlusChainStore:
; d = species, e = count. Stamps the magic alongside so the next read trusts
; what it finds.
	ld a, BANK(sPlusChainCheck)
	call OpenSRAM
	ld a, PLUS_CHAIN_MAGIC
	ld [sPlusChainCheck], a
	ld a, d
	ld [sPlusChainSpecies], a
	ld a, e
	ld [sPlusChainCount], a
	jp CloseSRAM

PlusChainReset::
; Called when a new game starts. The chain outlives a save file otherwise,
; since nothing in the normal new-game path goes near this corner of SRAM.
	ld de, 0
	jp PlusChainStore

PlusUpdateChain::
; Runs as a battle ends, while wBattleMode and the species are still live:
; CleanUpBattleRAM wipes both a moment later.
	ld a, [wBattleMode]
	dec a ; WILDMON
	ret nz ; a trainer's mon is not a wild encounter, so the chain stands

	; Only a win moves the count. A catch counts as one: it sets WIN too.
	ld a, [wBattleResult]
	and $f
	ret nz ; WIN is zero; fled, lost or drew leaves the chain alone

	; wTempWildMonSpecies, not wTempEnemyMonSpecies: catching a Transformed
	; mon overwrites the latter with Ditto, which is a vanilla bug this has no
	; business inheriting. This one is set by the encounter tables and by the
	; script command that starts a static battle, and survives until
	; CleanUpBattleRAM, which runs a moment after this.
	ld a, [wTempWildMonSpecies]
	and a
	ret z
	ld b, a

	call PlusChainLoad
	ld a, d
	cp b
	jr nz, .different

	inc e
	jr nz, .store
	dec e ; the count is a byte, so hold it at the top rather than wrap
	jr .store

.different
	ld d, b
	ld e, 1

.store
	call PlusChainStore
	ret

PlusChainRollsFor:
; b = the species about to be generated. Returns the DV roll allowance it has
; earned in a, or zero when it has earned none.
	call PlusChainLoad
	call CloseSRAM
	ld a, d
	and a
	ret z ; no chain at all

	cp b
	jr z, .same
	xor a
	ret ; the chain is on something else, so this mon gets nothing

.same
	; Walk the table from the longest chain down and take the first row the
	; count reaches. e holds the count.
	ld hl, PlusChainTiers
	ld c, PLUS_CHAIN_TIERS
.find
	ld a, [hli]
	cp e
	jr z, .found
	jr c, .found
	inc hl ; step over the roll count this row would have given
	dec c
	jr nz, .find
	xor a
	ret ; shorter than the first tier, so the game's own single roll stands

.found
	ld a, [hl]
	ret

PlusChainTiers:
; Longest chain first: the shortest chain that earns the row, then the rolls
; it earns. Held here rather than computed so the curve is one thing to read.
	db 40, 32 ; about one in 256
	db 30, 16 ; about one in 512
	db 20,  8 ; about one in 1024
	db 10,  4 ; about one in 2048
	assert PLUS_CHAIN_TIERS * 2 == PlusChainTiersEnd - PlusChainTiers
PlusChainTiersEnd:

PlusChainActive:
; Carry set when there is a chain worth showing, with it left in de.
	call PlusChainLoad
	call CloseSRAM
	ld a, d
	and a
	jr z, .none
	ld a, e
	and a
	jr z, .none
	scf
	ret

.none
	and a
	ret

PlusDrawMenuAccountBox::
; Stands in for the box the start menu clears behind its item descriptions.
; A running chain buys it two more rows on top of the usual five, so the two
; description lines below keep the rows they have always had: the game spaces
; those two rows apart, which leaves nothing free inside the original box.
	call PlusChainActive
	jr c, .with_chain

	hlcoord 0, 13
	lb bc, 5, 10
	call ClearBox
	hlcoord 0, 13
	lb bc, 3, 8 ; TextboxPalette wants the inside, not the whole box
	jp TextboxPalette

.with_chain
	hlcoord 0, 10
	lb bc, 8, 10
	call ClearBox
	hlcoord 0, 10
	lb bc, 6, 8
	jp TextboxPalette

PlusPrintChainStatus::
; Fills the two rows a running chain adds to the top of the start menu's
; description box: what is being chained, and how far in.
;
; Prints nothing when there is no chain, rather than a "none" line that would
; sit there for the whole game before the feature is ever used.
	call PlusChainActive
	ret nc

	ld a, e
	ld [wStringBuffer2], a ; PrintNum reads a byte out of memory, not a register
	ld a, d
	ld [wNamedObjectIndex], a
	call GetPokemonName ; leaves the name in de, ready for PlaceString
	hlcoord 0, 11
	call PlaceString

	hlcoord 0, 12
	ld de, .ChainString
	call PlaceString
	hlcoord 5, 12
	ld de, wStringBuffer2
	lb bc, 1, 3 ; one byte, three digits: the count stops at 255
	call PrintNum
	ret

.ChainString:
	db "Chain@"

PlusRollWildDVs::
; Stands in for the two BattleRandom calls a wild or static encounter makes to
; roll its DVs, and returns the pair in bc exactly as they did. A chain on this
; species buys re-rolls; anything else gets the single roll the game gives.
;
; Static encounters come through here too. They cannot be chained by beating
; them repeatedly, but the chain is written to SRAM as the battle ends, so
; beating one and resetting without saving keeps the increment.
	push de
	push hl

	; Only an actual wild or static encounter draws on the chain. Nothing else
	; can arrive here: LoadEnemyMon.InitDVs hands every other battle mode, out
	; of battle included, to GetTrainerDVs before the wild branch begins. The
	; check is kept so this routine reads correctly on its own.
	ld e, 0
	ld a, [wBattleMode]
	dec a ; WILDMON
	jr nz, .rolled_none
	ld a, [wTempWildMonSpecies]
	ld b, a
	call PlusChainRollsFor
	ld e, a

.rolled_none

	call BattleRandom
	ld b, a
	call BattleRandom
	ld c, a

	ld d, 1 ; draw from BattleRandom, the source the battle engine uses
	call PlusRerollDVs
	pop hl
	pop de
	ret

PlusBoostShinyDVs::
; bc holds the DV pair the game just rolled for a mon a script is handing over.
; Re-rolls it while wPlusShinyRolls allows.
;
; de points at where the caller is about to store these, so it is kept here.
; hl the farcall overwrites on the way in, so the call site is what saves that
; one; only bc changes.
	push de
	push hl

	ldh a, [rWBK]
	ld d, a
	ld a, BANK(wPlusShinyRolls)
	ldh [rWBK], a
	ld a, [wPlusShinyRolls]
	ld e, a
	xor a
	ld [wPlusShinyRolls], a ; an allowance is spent once, not left lying set
	ld a, d
	ldh [rWBK], a

	ld d, 0 ; draw from Random: nothing outside a battle needs the other one
	call PlusRerollDVs

	pop hl
	pop de
	ret

PlusRerollDVs:
; bc holds a DV pair that has already been rolled once. e is how many pairs may
; be examined in total, counting that one, or zero to leave the pair alone. d
; selects the source of any further rolls: zero for Random, nonzero for
; BattleRandom, which is what the battle engine uses so a link battle stays in
; step. Neither RNG touches de, so the count and the selector survive them.
;
; Re-rolls until the pair comes up shiny or the allowance runs out, and keeps
; whatever the last roll gave if it never does.
;
; This is the whole mechanism: shininess in this generation is nothing but the
; DVs, so another chance at one is another roll of them. That makes the number
; of rolls the only dial, and the odds follow it at about N in 8192. It also
; means a shiny found this way is a real one, with any of the eight Attack DVs
; a shiny can have, rather than one fixed pair forced into place.
	ld a, e
	and a
	ret z ; no allowance, so the roll the game already made stands

.roll
	call PlusIsShinyDVs
	ret c
	dec e
	ret z

	call .next
	ld b, a
	call .next
	ld c, a
	jr .roll

.next
	ld a, d
	and a
	jp z, Random
	jp BattleRandom

PlusIsShinyDVs:
; bc holds a DV pair. Returns carry when it is a shiny one.
;
; The same four tests CheckShininess makes, on DVs held in registers rather
; than in memory, so a roll can be judged before anything stores it.
	ld a, b
	and SHINY_ATK_MASK << 4
	jr z, .not_shiny

	ld a, b
	and %1111
	cp SHINY_DEF_DV
	jr nz, .not_shiny

	ld a, c
	and %1111 << 4
	cp SHINY_SPD_DV << 4
	jr nz, .not_shiny

	ld a, c
	and %1111
	cp SHINY_SPC_DV
	jr nz, .not_shiny

	scf
	ret

.not_shiny
	and a
	ret

PlusCheckWildOn::
; wScriptVar = 0 when the wild randomizer is off, or the mode plus one.
	call PlusGetWildMode
	jr c, .on
	xor a
	ld [wScriptVar], a
	ret

.on
	inc a
	ld [wScriptVar], a
	ret

PlusSetWildMode::
; Switch the wild randomizer to the mode in wScriptVar, or off if that is
; PLUS_WILD_SET_OFF, then rebuild the maps to match.
	ld a, [wScriptVar]
	cp NUM_PLUS_WILD_MODES
	jr nc, .off
rept PLUS_WILD_MODE_SHIFT
	add a
endr
	or 1 << PLUS_WILD_ENABLED_F
	ld d, a
	call PlusReadFlags
	and ~(PLUS_WILD_MODE_MASK | 1 << PLUS_WILD_ENABLED_F)
	or d
	call PlusWriteFlags
	jp PlusBuildWildMaps

.off
	call PlusReadFlags
	res PLUS_WILD_ENABLED_F, a
	call PlusWriteFlags
	jp PlusBuildWildMaps
