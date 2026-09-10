; Game Corner prize menu.
;
; The prize species are shuffled like any other, so the menu cannot use the
; strings baked into the map. This builds the same structure a MenuData block
; has in ROM (flags, row count, then one "@"-terminated row each) into
; wPlusPrizeMenuData, and the map's menu header points there instead. The
; vertical menu reads its rows with a plain `ld a, [de]`, so a WRAM address
; works with no engine change; the start menu already does the same thing.
;
; Rows are 16 bytes: the name padded out to column 11, then a four character
; right aligned price, then the terminator. That matches the vanilla spacing.

DEF PLUS_PRIZE_NAME_WIDTH  EQU 11
DEF PLUS_PRIZE_PRICE_WIDTH EQU 4

PlusBuildPrizeMenu::
; wScriptVar picks the room: 0 Goldenrod, anything else Celadon.
	ld a, [wScriptVar]
	and a
	ld de, PlusGoldenrodPrizes
	jr z, .got_room
	ld de, PlusCeladonPrizes
.got_room

	ld hl, wPlusPrizeMenuData
	ld a, STATICMENU_CURSOR
	ld [hli], a
	ld a, 4 ; three prizes and CANCEL
	ld [hli], a

	ld c, 3
.row
	push bc
	ld a, [de]
	inc de ; de now points at the price text
	ld [wNamedObjectIndex], a
	push de
	push hl
	call GetPokemonName ; writes wStringBuffer1
	pop hl

	ld de, wStringBuffer1
	ld b, PLUS_PRIZE_NAME_WIDTH
.copy_name
	ld a, [de]
	cp '@'
	jr z, .pad
	ld [hli], a
	inc de
	dec b
	jr nz, .copy_name
	jr .price

.pad
	ld a, ' '
.pad_loop
	ld [hli], a
	dec b
	jr nz, .pad_loop

.price
	pop de
	ld b, PLUS_PRIZE_PRICE_WIDTH
.copy_price
	ld a, [de]
	ld [hli], a
	inc de
	dec b
	jr nz, .copy_price
	ld a, '@'
	ld [hli], a

	pop bc
	dec c
	jr nz, .row

	ld de, .Cancel
.copy_cancel
	ld a, [de]
	ld [hli], a
	inc de
	cp '@'
	jr nz, .copy_cancel
	ret

.Cancel:
	db "CANCEL@"

; species, then the price right aligned in four characters
PlusGoldenrodPrizes:
	db ABRA,      " 100"
	db CUBONE,    " 800"
	db WOBBUFFET, "1500"

PlusCeladonPrizes:
	db PIKACHU,  "2222"
	db PORYGON,  "5555"
	db LARVITAR, "8888"
