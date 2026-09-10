ObjectActionPairPointers:
; entries correspond to OBJECT_ACTION_* constants (see constants/map_object_constants.asm)
	table_width 2 + 2
	;  normal action,                  frozen action
	dw SetFacingStanding,              SetFacingStanding
	dw SetFacingStandAction,           SetFacingCurrent
	dw SetFacingStepAction,            SetFacingCurrent
	dw SetFacingBumpAction,            SetFacingCurrent
	dw SetFacingCounterclockwiseSpin,  SetFacingCurrent
	dw SetFacingCounterclockwiseSpin2, SetFacingStanding
	dw SetFacingFish,                  SetFacingFish
	dw SetFacingShadow,                SetFacingStanding
	dw SetFacingEmote,                 SetFacingEmote
	dw SetFacingBigDollSym,            SetFacingBigDollSym
	dw SetFacingBounce,                SetFacingFreezeBounce
	dw SetFacingWeirdTree,             SetFacingCurrent
	dw SetFacingBigDollAsym,           SetFacingBigDollAsym
	dw SetFacingBigDoll,               SetFacingBigDoll
	dw SetFacingBoulderDust,           SetFacingStanding
	dw SetFacingGrassShake,            SetFacingStanding
	dw SetFacingSkyfall,               SetFacingCurrent
	assert_table_length NUM_OBJECT_ACTIONS

SetFacingStanding:
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], STANDING
	ret

SetFacingCurrent:
	call GetSpriteDirection
	or FACING_STEP_DOWN_0 ; useless
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], a
	ret

SetFacingStandAction:
	ld hl, OBJECT_FACING
	add hl, bc
	ld a, [hl]
	and 1
	jr nz, SetFacingStepAction
	jp SetFacingCurrent

SetFacingStepAction:
	ld hl, OBJECT_FLAGS1
	add hl, bc
	bit SLIDING_F, [hl]
	jp nz, SetFacingCurrent

	ld hl, OBJECT_STEP_FRAME
	add hl, bc
; plus: the counter advances once per overworld iteration and the top two bits
; of its cycle pick the sprite frame. At 60 fps there are twice as many
; iterations per tile, so it only advances on half of them and the legs move at
; the speed they do at 30 fps.
	lb de, %00001111, 1 ; plus
	call DoubleStepFrameWhenRunning ; plus
	call AdvanceStepFrame60

	rrca
	rrca
	maskbits NUM_DIRECTIONS
	ld d, a

	call GetSpriteDirection
	or FACING_STEP_DOWN_0 ; useless
	or d
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], a
	ret

SetFacingSkyfall:
	ld hl, OBJECT_FLAGS1
	add hl, bc
	bit SLIDING_F, [hl]
	jp nz, SetFacingCurrent

	ld hl, OBJECT_STEP_FRAME
	add hl, bc
	lb de, %00001111, 2 ; plus
	call AdvanceStepFrame60

	rrca
	rrca
	maskbits NUM_DIRECTIONS
	ld d, a

	call GetSpriteDirection
	or FACING_STEP_DOWN_0 ; useless
	or d
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], a
	ret

SetFacingBumpAction:
	ld hl, OBJECT_FLAGS1
	add hl, bc
	bit SLIDING_F, [hl]
	jp nz, SetFacingCurrent

	ld hl, OBJECT_STEP_FRAME
	add hl, bc
	lb de, %00011111, 1 ; plus
	call AdvanceStepFrame60

	rrca
	rrca
	rrca
	maskbits NUM_DIRECTIONS
	ld d, a

	call GetSpriteDirection
	or FACING_STEP_DOWN_0 ; useless
	or d
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], a
	ret

SetFacingCounterclockwiseSpin:
	call CounterclockwiseSpinAction
	ld hl, OBJECT_DIRECTION
	add hl, bc
	ld a, [hl]
	or FACING_STEP_DOWN_0 ; useless
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], a
	ret

SetFacingCounterclockwiseSpin2:
	call CounterclockwiseSpinAction
	jp SetFacingStanding

CounterclockwiseSpinAction:
; Here, OBJECT_STEP_FRAME consists of two 2-bit components,
; using only bits 0,1 and 4,5.
; bits 0,1 is a timer (4 overworld frames, 8 with the 60 fps option on)
; bits 4,5 determines the facing - the direction is counterclockwise.
	ld hl, OBJECT_STEP_FRAME
	add hl, bc
	ld a, [hl]
	and %11110000
	ld e, a

	ld a, [hl]
	inc a
	and %00001111
	ld d, a
	ld a, 4 ; plus: iterations per facing, doubled at 60 fps
	call ScaleDuration60
	; plus: compare against the last in-range value so the test is >=, not ==.
	; plus: toggling the frame rate mid-spin can leave a timer above the 30 fps
	; plus: threshold, and an equality test would never catch it.
	dec a
	cp d
	jr nc, .ok

	ld d, 0
	ld a, e
	add $10
	and %00110000
	ld e, a

.ok
	ld a, d
	or e
	ld [hl], a

	swap e
	ld d, 0
	ld hl, .facings
	add hl, de
	ld a, [hl]
	ld hl, OBJECT_DIRECTION
	add hl, bc
	ld [hl], a
	ret

.facings:
	db OW_DOWN
	db OW_RIGHT
	db OW_UP
	db OW_LEFT

SetFacingFish:
	call GetSpriteDirection
	rrca
	rrca
	add FACING_FISH_DOWN
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], a
	ret

SetFacingShadow:
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_SHADOW
	ret

SetFacingEmote:
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_EMOTE
	ret

SetFacingBigDollSym:
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_BIG_DOLL_SYM
	ret

SetFacingBounce:
	ld hl, OBJECT_STEP_FRAME
	add hl, bc
	lb de, %00001111, 1 ; plus
	call AdvanceStepFrame60
	and %00001000
	jr z, SetFacingFreezeBounce
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_STEP_UP_0
	ret

SetFacingFreezeBounce:
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_STEP_DOWN_0
	ret

SetFacingWeirdTree:
	ld hl, OBJECT_STEP_FRAME
	add hl, bc
	lb de, %00001111, 1 ; plus
	call AdvanceStepFrame60
	maskbits NUM_DIRECTIONS, 2
	rrca
	rrca
	add FACING_WEIRD_TREE_0
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], a
	ret

SetFacingBigDollAsym:
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_BIG_DOLL_ASYM
	ret

SetFacingBigDoll:
	ld a, [wVariableSprites + SPRITE_BIG_DOLL - SPRITE_VARS]
	ld d, FACING_BIG_DOLL_SYM ; symmetric
	cp SPRITE_BIG_SNORLAX
	jr z, .ok
	cp SPRITE_BIG_LAPRAS
	jr z, .ok
	ld d, FACING_BIG_DOLL_ASYM ; asymmetric

.ok
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], d
	ret

SetFacingBoulderDust:
	ld hl, OBJECT_STEP_FRAME
	add hl, bc
	lb de, %00000011, 1 ; plus
	call AdvanceStepFrame60

	ld hl, OBJECT_FACING
	add hl, bc
	and 2
	ld a, FACING_BOULDER_DUST_1
	jr z, .ok
	assert FACING_BOULDER_DUST_1 + 1 == FACING_BOULDER_DUST_2
	inc a
.ok
	ld [hl], a
	ret

SetFacingGrassShake:
	ld hl, OBJECT_STEP_FRAME
	add hl, bc
	lb de, %00000111, 1 ; plus
	call AdvanceStepFrame60
	ld hl, OBJECT_FACING
	add hl, bc
	and 4
	ld a, FACING_GRASS_1
	jr z, .ok
	assert FACING_GRASS_1 + 1 == FACING_GRASS_2
	inc a
.ok
	ld [hl], a
	ret

; plus: an object's animation counter advances once per overworld iteration,
; and the 60 fps option runs that loop twice as often. Bit 7 of the counter
; marks which half of a 30 fps frame the current iteration is, so the counter
; itself only moves on every other one and the animation keeps its speed. hl
; points at the counter, d holds its wrap mask (with bit 7 clear) and e the
; step to add. Returns the wrapped counter in a. Preserves bc, d and hl.
AdvanceStepFrame60:
	ld a, [wOptions2]
	bit FRAME_RATE_60_F, a
	jr z, .advance
	ld a, [hl]
	xor 1 << 7
	ld [hl], a
	and 1 << 7
	jr nz, .hold

.advance
	ld a, [hl]
	and d
	add e
	and d
	ld e, a
	ld a, [hl]
	and 1 << 7
	or e
	ld [hl], a
	ld a, e
	ret

.hold
	ld a, [hl]
	and d
	ret

; plus: a running step covers a tile in half the iterations a walking one does,
; so its animation counter has to advance twice as fast for the legs to keep
; pace with the feet. Takes the counter step in e and returns it doubled while
; the object is part way through a running step. Preserves bc, d and hl.
DoubleStepFrameWhenRunning:
	push hl
	ld hl, OBJECT_WALKING
	add hl, bc
	ld a, [hl]
	pop hl
	cp STANDING
	ret z
	and %00001100
	cp STEP_RUN << 2
	ret nz
	sla e
	ret
