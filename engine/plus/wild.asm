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
	ld b, 0 ; not another trainer's mon
	farcall GivePoke
	ld a, b
	ld [wScriptVar], a
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
