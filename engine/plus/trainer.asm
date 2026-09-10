; Trainer roster randomizer
; See docs/plus.md for the design notes.

PlusRandomizeTrainerMon::
; Called from TrainerType1 once wCurPartyLevel and wCurPartySpecies have been
; read for the mon that is about to be added to the enemy party. Replaces the
; species with a random one of the same level and returns everything else as
; it found it.

; The roll is not seeded: a rematch against the same trainer fields a
; different team on purpose. Only TRAINERTYPE_NORMAL parties reach here, so
; gym leaders, the rival, the Elite Four and anyone carrying custom moves or
; a held item keep their vanilla roster.
	ld a, [wPlusFlags]
	bit PLUS_TRAINERS_F, a
	ret z

	push bc
	push de
	push hl

	call PlusPickTrainerBasic
	ld b, a
	call PlusTrainerEffectiveLevel
	ld c, a
	call PlusEvolveTrainerMon
	ld a, b
	ld [wCurPartySpecies], a

	pop hl
	pop de
	pop bc
	ret

PlusPickTrainerBasic:
; Returns a random basic-stage species from the band that matches
; wCurPartyLevel. The three bands fall through into one another, so each label
; selects a superset of the one below it.
	ld a, [wCurPartyLevel]
	cp PLUS_TRAINER_LATE_LEVEL
	jr nc, .late
	cp PLUS_TRAINER_MID_LEVEL
	jr nc, .mid
	ld hl, PlusTrainerBasicsEarly
	jr .got_band
.mid
	ld hl, PlusTrainerBasicsMid
	jr .got_band
.late
	ld hl, PlusTrainerBasicsLate
.got_band
	push hl
	ld c, 0
.count
	ld a, [hli]
	cp -1
	jr z, .counted
	inc c
	jr .count
.counted
	ld a, c
	call RandomRange
	pop hl
	ld e, a
	ld d, 0
	add hl, de
	ld a, [hl]
	ret

PlusTrainerEffectiveLevel:
; Evolution thresholds are scaled by 4/3 below level 30 and by 8/7 at 30 and
; above, so that a randomized team is a stage behind a hand-built one rather
; than fully evolved from the first route. Discounting the level once is the
; same comparison and far cheaper than scaling every threshold: L * 3/4 is
; L - L/4, and L * 7/8 is L - L/8.
	ld a, [wCurPartyLevel]
	ld e, a
	cp PLUS_TRAINER_LATE_LEVEL
	jr nc, .eighth
	srl a
	srl a
	jr .discount
.eighth
	srl a
	srl a
	srl a
.discount
	ld d, a
	ld a, e
	sub d
	ret

PlusEvolveTrainerMon:
; b = species, c = effective level. Walks b forward along its own line for as
; long as an evolution applies, choosing at random when several do at once:
; that is what branches Tyrogue between the three Hitmons and Eevee between
; its five stones and times of day.

; Gen 2 lines are at most two steps deep and none of them loops back on
; itself, so the walk always reaches a species with nothing left to apply.
.chain
	call PlusGetEvosPointer
	push hl
	ld d, 0
.count
	call PlusNextTrainerEvolution
	jr c, .counted
	inc d
	inc hl
	jr .count
.counted
	pop hl
	ld a, d
	and a
	ret z
	call RandomRange
	ld d, a
.pick
	call PlusNextTrainerEvolution
	ret c
	ld a, d
	and a
	jr z, .evolve
	dec d
	inc hl
	jr .pick
.evolve
	call PlusGetEvosByte
	ld b, a
	jr .chain

PlusNextTrainerEvolution:
; Advances hl to the target species byte of the next evolution of species b
; that applies at effective level c, and returns carry clear. Returns carry
; set once the entry list runs out.
.entry
	call PlusGetEvosByte
	and a
	jr z, .end
	cp EVOLVE_LEVEL
	jr z, .by_level
	cp EVOLVE_STAT
	jr z, .by_stat
	cp EVOLVE_HAPPINESS
	jr z, .by_happiness
	; EVOLVE_ITEM and EVOLVE_TRADE. Neither has a level to work from, and
	; both stand for a stretch of the game rather than a moment in it, so
	; they share one threshold late enough to feel earned.
	inc hl ; item
	ld e, PLUS_EVO_ITEM_LEVEL
	jr .check
.by_level
	call PlusGetEvosByte
	ld e, a
	jr .check
.by_stat
	; Tyrogue is the only user, and all three of its branches read level 20.
	call PlusGetEvosByte
	ld e, a
	inc hl ; attack against defense
	jr .check
.by_happiness
	; A baby raised by a trainer is friendly early; Golbat and Chansey take
	; the same amount of care that a stone would.
	inc hl ; time of day
	ld e, PLUS_EVO_ITEM_LEVEL
	ld a, b
	cp PICHU
	jr z, .baby
	cp CLEFFA
	jr z, .baby
	cp IGGLYBUFF
	jr z, .baby
	cp TOGEPI
	jr z, .baby
	jr .check
.baby
	ld e, PLUS_EVO_BABY_LEVEL
.check
	ld a, c
	cp e
	ret nc
	inc hl ; target species
	jr .entry
.end
	scf
	ret

PlusGetEvosPointer:
; hl = the evolution and attack data for species b
	ld a, b
	dec a
	ld l, a
	ld h, 0
	add hl, hl
	ld de, EvosAttacksPointers
	add hl, de
	call PlusGetEvosByte
	ld e, a
	call PlusGetEvosByte
	ld d, a
	ld h, d
	ld l, e
	ret

PlusGetEvosByte:
; a = the byte at hl in the evolution and attack data, then hl advances
	ld a, BANK(EvosAttacksPointers)
	call GetFarByte
	inc hl
	ret

PlusCheckTrainersEnabled::
; Script hook. Leaves TRUE in wScriptVar while the trainer randomizer is on.
	ld a, [wPlusFlags]
	bit PLUS_TRAINERS_F, a
	ld a, TRUE
	jr nz, .store
	xor a
.store
	ld [wScriptVar], a
	ret

PlusToggleTrainers::
; Script hook. Flips the trainer randomizer on or off.
	ld a, [wPlusFlags]
	xor 1 << PLUS_TRAINERS_F
	ld [wPlusFlags], a
	ret
