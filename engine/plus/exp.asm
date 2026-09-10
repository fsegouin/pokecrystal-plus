; Catch-up EXP booster. See docs/plus.md.

PlusCatchUpExpBoost::
; Called from GiveExperiencePoints once per recipient, after the traded,
; trainer battle and Lucky Egg boosts have been applied to hProduct.
; wCurPartyMon selects the recipient, so a participant that was not on the
; field when the enemy fainted is still measured against its own level.
; A recipient below the fainted enemy's level gets one more 1.5x for every
; started 3 levels of the gap: gap 1-2 is 1.5x, 3-5 is 2.25x, 6-8 is 3.375x.
	ld a, [wPlusFlags]
	bit PLUS_EXP_BOOST_F, a
	ret z

	ld a, MON_LEVEL
	call GetPartyParamLocation
	ld a, [wEnemyMonLevel]
	sub [hl]
	ret z
	ret c ; the recipient is already at or above the enemy's level

.loop
	push af
	call .BoostOnce
	pop af
	sub 3
	jr nc, .loop
	ret

.BoostOnce:
; Multiply the 16-bit gain in hProduct + 2 by 1.5, saturating at $ffff.
; A wide gap asks for more than a dozen of these, and the exp bar reads a
; wrapped total as a genuine, enormous gain rather than as an overflow.
	ldh a, [hProduct + 2]
	ld h, a
	ldh a, [hProduct + 3]
	ld l, a
	ld d, h
	ld e, l
	srl d
	rr e
	add hl, de
	jr nc, .no_overflow
	ld hl, $ffff

.no_overflow
	ld a, h
	ldh [hProduct + 2], a
	ld a, l
	ldh [hProduct + 3], a
	ret

PlusToggleExpBoost::
; Script hook for the Celadon Cafe scientist. Flips PLUS_EXP_BOOST_F and
; reports the new state in wScriptVar.
	ld hl, wPlusFlags
	ld a, 1 << PLUS_EXP_BOOST_F
	xor [hl]
	ld [hl], a
	and 1 << PLUS_EXP_BOOST_F
	jr PlusSetScriptVar

PlusCheckExpBoost::
; Script hook: wScriptVar = TRUE while the booster is on.
	ld a, [wPlusFlags]
	and 1 << PLUS_EXP_BOOST_F
	; fallthrough

PlusSetScriptVar:
; wScriptVar = TRUE if a is nonzero, FALSE otherwise.
	and a
	ld a, FALSE
	jr z, .store
	ld a, TRUE

.store
	ld [wScriptVar], a
	ret
