; Repel top-off. See docs/plus.md.
;
; wPlusFlags carries the state: bits 5-6 hold the kind of repel last used
; (PLUS_REPEL_KIND_*), bit 7 is auto-renew. Both are saved with the game.

PlusRepelSteps:
; Indexed by kind - 1. The step counts are the ones RepelEffect,
; SuperRepelEffect and MaxRepelEffect load.
	db REPEL,       100
	db SUPER_REPEL, 200
	db MAX_REPEL,   250

PlusRepelUsed::
; Called from UseRepel once a repel from the pack has taken effect, with the
; item in wCurItem. Remembers the kind for the top-off and leaves auto-renew
; off: a repel used by hand starts over, and the offer comes when it runs out.
	ld a, [wCurItem]
	ld b, PLUS_REPEL_KIND_REPEL
	cp REPEL
	jr z, .got_kind
	inc b
	cp SUPER_REPEL
	jr z, .got_kind
	inc b
.got_kind
	ld c, 0
	jr PlusRepelSetState

PlusRepelAutoRenew::
; Called from DoRepelStep on the step a repel runs out. With auto-renew on,
; quietly use another; with none left, switch auto-renew off, so the usual
; message plays and nothing is offered.
	call PlusReadFlags
	bit PLUS_REPEL_AUTO_F, a
	ret z
	call PlusRepelFindRefill
	jr nc, .none_left
	call PlusRepelRefill
	ld c, 1 << PLUS_REPEL_AUTO_F
	jr PlusRepelSetState

.none_left
	call PlusReadFlags
	res PLUS_REPEL_AUTO_F, a
	jp PlusWriteFlags

PlusRepelEnterMap::
; Called from EnterMap. Walking into a building ends auto-renew; the repel
; itself keeps counting down as usual. Caves and gates are not buildings.
	call GetMapEnvironment
	cp INDOOR
	ret nz
	call PlusReadFlags
	res PLUS_REPEL_AUTO_F, a
	jp PlusWriteFlags

PlusRepelCheckRefill::
; Script hook: wScriptVar = TRUE when the pack holds a repel to top off with,
; and its name is in wStringBuffer1 for the offer.
	call PlusRepelFindRefill
	ld a, FALSE
	jr nc, .store
	call PlusRepelNameItem
	ld a, TRUE
.store
	ld [wScriptVar], a
	ret

PlusRepelTopOff::
; Script hook for a yes to the offer: use one and switch auto-renew on.
	call PlusRepelFindRefill
	ret nc ; the offer is only made with one in the pack
	call PlusRepelRefill
	ld c, 1 << PLUS_REPEL_AUTO_F
	; fallthrough

PlusRepelSetState:
; Store kind b and the auto-renew bit given in c (0 or 1 << PLUS_REPEL_AUTO_F).
	assert PLUS_REPEL_KIND_LO_F == 5, "the shift below assumes the kind starts at bit 5"
	call PlusReadFlags
	and ~(PLUS_REPEL_KIND_MASK | 1 << PLUS_REPEL_AUTO_F)
	or c
	ld c, a
	ld a, b
	swap a
	add a
	or c
	jp PlusWriteFlags

PlusRepelFindRefill:
; Find a repel in the pack to top off with: the kind last used first, then
; the weakest there is. Returns carry with the kind in b and the item in
; wCurItem, or no carry when the pack holds none.
	call PlusReadFlags
	and PLUS_REPEL_KIND_MASK
	swap a
	srl a
	ld b, a
	and a
	jr z, .scan
	call .Try
	ret c
.scan
	ld b, PLUS_REPEL_KIND_REPEL
.loop
	call .Try
	ret c
	inc b
	ld a, b
	cp NUM_PLUS_REPEL_KINDS + 1
	jr c, .loop
	and a
	ret

.Try:
; Carry if the pack holds kind b. Preserves b.
	call PlusRepelEntry
	ld a, [hl]
	ld [wCurItem], a
	ld hl, wNumItems
	jp CheckItem

PlusRepelRefill:
; Use one repel of kind b, already in wCurItem, and start its step count.
; Preserves b.
	push bc
	ld a, 1
	ld [wItemQuantityChange], a
	ld a, -1
	ld [wCurItemQuantity], a ; no slot hint: search the pocket
	ld hl, wNumItems
	call TossItem
	pop bc
	call PlusRepelEntry
	inc hl
	ld a, [hl]
	ld [wRepelEffect], a
	ret

PlusRepelEntry:
; hl = the PlusRepelSteps row for kind b. Preserves bc.
	ld a, b
	dec a
	add a
	ld e, a
	ld d, 0
	ld hl, PlusRepelSteps
	add hl, de
	ret

PlusRepelNameItem:
; The name of wCurItem in wStringBuffer1. Preserves bc.
	ld a, [wCurItem]
	ld [wNamedObjectIndex], a
	jp GetItemName

PlusRepelWoreOffScript::
; Runs in place of RepelWoreOffScript. With a repel left in the pack it
; offers to top off, and a yes keeps the repel going until the player next
; goes indoors or runs out.
	opentext
	callasm PlusRepelCheckRefill
	iftrue .Offer
	writetext PlusRepelWoreOffText
	waitbutton
	closetext
	end

.Offer:
	writetext PlusRepelOfferText
	yesorno
	iffalse .Done
	callasm PlusRepelTopOff
	writetext PlusRepelToppedOffText
	waitbutton
.Done:
	closetext
	end

PlusRepelWoreOffText:
	text_far _RepelWoreOffText
	text_end

PlusRepelOfferText:
	text "REPEL's effect"
	line "wore off."

	para "Use another"
	line "@"
	text_ram wStringBuffer1
	text "?"
	done

PlusRepelToppedOffText:
	text "It will be topped"
	line "off until you go"
	cont "indoors."
	done
