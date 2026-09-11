; Type matchup markers on the battle move list. See docs/plus.md.

PlusMarkMoveMatchups::
; Called from MoveSelectionScreen once the moves are listed. Marks each of the
; player's moves with how it fares against the enemy's current types. Only the
; battle's own move list: Mimic's list and the Ether menu are left alone.
	ld a, [wMoveSelectionMenuType]
	and a
	ret nz
	call PlusLoadMatchupArrow
	; fallthrough

PlusPlaceMatchupMarkers::
; Write a marker, or nothing, in the cell after each move name. The matchup
; routine reads the move's type and the attacker from the battle variables,
; so both are borrowed and put back.
	ldh a, [hBattleTurn]
	push af
	ld a, [wPlayerMoveStructType]
	push af
	xor a
	ldh [hBattleTurn], a
	ld hl, wBattleMonMoves
	decoord PLUS_MATCHUP_COLUMN, 17 - NUM_MOVES
	ld b, NUM_MOVES
.loop
	ld a, [hli]
	and a
	jr z, .done
	push hl
	push de
	push bc
	call PlusMatchupMarker
	pop bc
	pop de
	pop hl
	and a
	jr z, .next
	ld [de], a
.next
	ld a, e
	add SCREEN_WIDTH
	ld e, a
	jr nc, .same_page
	inc d
.same_page
	dec b
	jr nz, .loop
.done
	pop af
	ld [wPlayerMoveStructType], a
	pop af
	ldh [hBattleTurn], a
	ret

PlusMatchupMarker:
; a = a move. Returns the tile to mark it with, or 0 for none.
	dec a
	ld hl, Moves + MOVE_EFFECT
	ld bc, MOVE_LENGTH
	call AddNTimes
	ld a, BANK(Moves)
	call GetFarByte
	ld c, a
	inc hl
	ld a, BANK(Moves)
	call GetFarByte
	and a
	ret z ; no power: a status move, which the chart does not decide
	inc hl
	ld a, BANK(Moves)
	call GetFarByte
	ld b, a
	ld a, c
	cp EFFECT_COUNTER
	jr z, .none
	cp EFFECT_MIRROR_COAT
	jr z, .none
	cp EFFECT_HIDDEN_POWER
	call z, PlusHiddenPowerType

	ld a, b
	ld [wPlayerMoveStructType], a
	push bc
	farcall BattleCheckTypeMatchup
	pop bc
	ld a, [wTypeMatchup]
	and a
	jr z, .no_effect
	ld e, a
	; Fixed damage ignores the chart, except that an immunity stops it.
	ld a, c
	cp EFFECT_STATIC_DAMAGE
	jr z, .none
	cp EFFECT_LEVEL_DAMAGE
	jr z, .none
	cp EFFECT_PSYWAVE
	jr z, .none
	cp EFFECT_SUPER_FANG
	jr z, .none
	ld a, e
	cp EFFECTIVE
	jr z, .none
	ld a, '▼'
	ret c
	ld a, PLUS_MATCHUP_ARROW_TILE
	ret

.no_effect
	ld a, '×'
	ret

.none
	xor a
	ret

PlusHiddenPowerType:
; b = the type Hidden Power takes from the player's DVs, worked out the way
; HiddenPowerDamage does it. Preserves c.
	ld a, [wBattleMonDVs]
	and %0011
	ld b, a
	ld a, [wBattleMonDVs]
	and %0011 << 4
	swap a
	add a
	add a
	or b
	inc a ; skip Normal
	cp BIRD
	jr c, .done
	inc a
	cp UNUSED_TYPES
	jr c, .done
	add UNUSED_TYPES_END - UNUSED_TYPES
.done
	ld b, a
	ret

PlusLoadMatchupArrow:
; Copy the game's own up arrow into the slot the markers borrow. Menus reload
; the font over it, so this runs every time the list is drawn.
	ld de, FontsExtra2_UpArrowGFX
	ld hl, vTiles1 tile (PLUS_MATCHUP_ARROW_TILE - $80)
	lb bc, BANK(FontsExtra2_UpArrowGFX), 1
	jp Get2bpp
