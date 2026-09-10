; plus: the battle HUD name row, with the nickname condensed.
;
; Vanilla puts the nickname on one row and the gender symbol and level on the
; next. It has to: the row is eleven tiles and a ten character name fills all
; but one of them. The Japanese version fits everything on one line only
; because its nicknames cap at five characters, not because its font is
; smaller. Both draw the same 8x8 grid.
;
; So only the NAME is condensed, to five pixels a character. The gender
; symbol, the ":L" and the level digits are the game's own graphics at their
; own size, copied into the narrow font at build time by
; tools/make_half_font.py. Nothing about them changes except their spacing.
;
; Because the name ends part way through a tile, anything after it would sit a
; few pixels late if it came from the tilemap, which only addresses whole
; tiles. Drawing the whole row into tiles of its own instead lets each piece
; start exactly where the last one ended, which is what the Japanese row looks
; like. The composed tiles live in blank slots of the standard font block:
; those ids map to hiragana, which an English build never places.
;
; Worst case is a ten character name, a gender symbol and a three digit level:
; 50 + 8 + 24 pixels, which is 82 of the 88 an eleven tile row holds. A three
; digit level drops the ":L", exactly as vanilla's PrintLevel does.

PlusHUDFont:
INCBIN "gfx/font/font_half.1bpp"

; glyph indices past the narrow set, see tools/make_half_font.py
DEF PLUS_HUD_GLYPH_MALE   EQU PLUS_HUD_WIDE_FIRST + 0
DEF PLUS_HUD_GLYPH_FEMALE EQU PLUS_HUD_WIDE_FIRST + 1
DEF PLUS_HUD_GLYPH_LV     EQU PLUS_HUD_WIDE_FIRST + 2
DEF PLUS_HUD_GLYPH_DIGIT  EQU PLUS_HUD_WIDE_FIRST + 3
; each status tag is three cells of art, in the order SLP PSN BRN FRZ PAR
DEF PLUS_HUD_GLYPH_TAG    EQU PLUS_HUD_WIDE_FIRST + 13
DEF PLUS_HUD_TAG_SLP EQU PLUS_HUD_GLYPH_TAG + 0 * 3
DEF PLUS_HUD_TAG_PSN EQU PLUS_HUD_GLYPH_TAG + 1 * 3
DEF PLUS_HUD_TAG_BRN EQU PLUS_HUD_GLYPH_TAG + 2 * 3
DEF PLUS_HUD_TAG_FRZ EQU PLUS_HUD_GLYPH_TAG + 3 * 3
DEF PLUS_HUD_TAG_PAR EQU PLUS_HUD_GLYPH_TAG + 4 * 3

PlusHUDComposeEnemyRow::
; b = gender character, c = status byte. Returns the tiles filled in b.
	call PlusHUDBuildEnemyRow
	push bc
	ldh a, [rWBK]
	push af
	ld a, BANK(wPlusHUDRow)
	ldh [rWBK], a
	ld hl, wPlusHUDLastEnemy
	call PlusHUDNeedsUpload
	jr z, PlusHUDDoneUploading
	ld de, wPlusHUDRow
	ld hl, vTiles1 tile (PLUS_HUD_ENEMY_TILE - $80)
	lb bc, BANK(PlusHUDFont), PLUS_HUD_ENEMY_RUN
	call Get1bpp
	ld de, wPlusHUDRow + PLUS_HUD_ENEMY_RUN * TILE_1BPP_SIZE
	ld hl, vTiles1 tile (PLUS_HUD_ENEMY_TILE2 - $80)
	lb bc, BANK(PlusHUDFont), PLUS_HUD_TILES - PLUS_HUD_ENEMY_RUN
	call Get1bpp
	ld hl, wPlusHUDLastEnemy
	call PlusHUDRememberRow
	jr PlusHUDDoneUploading

PlusHUDComposePlayerRow::
; The player's tiles are a different run of blank slots, so the two HUDs
; cannot overwrite each other.
	call PlusHUDBuildPlayerRow
	push bc
	ldh a, [rWBK]
	push af
	ld a, BANK(wPlusHUDRow)
	ldh [rWBK], a
	ld hl, wPlusHUDLastPlayer
	call PlusHUDNeedsUpload
	jr z, PlusHUDDoneUploading
	ld de, wPlusHUDRow
	ld hl, vTiles1 tile (PLUS_HUD_PLAYER_TILE - $80)
	lb bc, BANK(PlusHUDFont), PLUS_HUD_PLAYER_RUN
	call Get1bpp
	ld de, wPlusHUDRow + PLUS_HUD_PLAYER_RUN * TILE_1BPP_SIZE
	ld hl, vTiles1 tile (PLUS_HUD_PLAYER_TILE2 - $80)
	lb bc, BANK(PlusHUDFont), PLUS_HUD_TILES - PLUS_HUD_PLAYER_RUN
	call Get1bpp
	ld hl, wPlusHUDLastPlayer
	call PlusHUDRememberRow
	; fallthrough

PlusHUDDoneUploading:
; With the LCD on these copies go through Request1bpp, which blocks until
; VBlank has taken every tile and never touches rWBK, so the bank selected
; above is still selected when VBlank reads the buffer.
	pop af
	ldh [rWBK], a
	pop bc ; the tile count, from before the upload used bc
	ret

PlusHUDNeedsUpload:
; hl = this row's copy of what was last sent. Returns nz when the tiles should
; go to VRAM now.
;
; Two reasons not to send them. The row is rebuilt on every HUD redraw, which
; happens after every animation and every turn, but its contents only change
; on a switch, a level up or a status change, so almost every rebuild is
; identical to the last and there is nothing to send.
;
; The second reason is the important one. With the LCD on, the upload goes
; through Request1bpp, which sets the request up and then waits for VBlank to
; take it. Only VBlank_Normal and VBlank_DMATransfer serve those requests, and
; battle animations install VBlank_CutsceneCGB, so a request made under one of
; those is never served and the wait never ends. Insisting on VBLANK_NORMAL is
; stricter than the hang needs and costs nothing here. Leaving it for the next
; redraw costs at most
; a frame or two, because the HUD is redrawn so often.
	ld de, wPlusHUDRow
	ld bc, wPlusHUDRowEnd - wPlusHUDRow
.compare
	ld a, [de]
	inc de
	cp [hl]
	jr nz, .changed
	inc hl
	dec bc
	ld a, b
	or c
	jr nz, .compare
	xor a ; unchanged, so nothing to send
	ret

.changed
	ldh a, [hVBlank]
	and a ; VBLANK_NORMAL is zero
	jr nz, .not_now
	ld a, TRUE
	and a
	ret

.not_now
; some other VBlank handler is installed, so try again on the next redraw
	xor a
	ret

PlusHUDRememberRow:
; hl = this row's copy of what was last sent. Records what just went to VRAM.
	ld d, h
	ld e, l
	ld hl, wPlusHUDRow
	ld bc, wPlusHUDRowEnd - wPlusHUDRow
	jp CopyBytes

PlusHUDInvalidate::
; Forget what was last sent, so the next redraw of each row sends it again.
;
; The composed tiles live in the standard font block, so anything that reloads
; that block blanks them while the saved copies still claim they are up to
; date. Every battle start does exactly that, and so does coming back from the
; party menu or the bag, which is why this hangs off _LoadBattleFontsHPBar:
; that runs on all six of those paths.
;
; Byte 0 of a row is the top pixel row of its first tile, and no glyph in the
; font has ink there, so -1 can never match a row that was really built.
	ldh a, [rWBK]
	push af
	ld a, BANK(wPlusHUDLastEnemy)
	ldh [rWBK], a
	ld a, -1
	ld [wPlusHUDLastEnemy], a
	ld [wPlusHUDLastPlayer], a
	pop af
	ldh [rWBK], a
	ret

PlusHUDBuildEnemyRow::
; Separate from the upload so it can be run and inspected on its own, and
; because the upload waits on VBlank while this does not.
	ld a, [wEnemyMonLevel]
	ld hl, wEnemyMonNickname
	jr PlusHUDBuildRow

PlusHUDBuildPlayerRow::
	ld a, [wBattleMonLevel]
	ld hl, wBattleMonNickname
	; fallthrough

PlusHUDBuildRow:
; a = level, hl = '@' terminated name, b = gender character or 0 for none,
; c = status byte. Returns the tiles the row filled in b.
;
; The row is measured before anything is drawn, so the whole of it, name
; included, can be set against the right hand end of the HP bar below. Every
; piece then follows the one before it with nothing between them, and the
; slack all ends up on the left.
	ld d, a
	ldh a, [rWBK]
	push af
	ld a, BANK(wPlusHUDRow)
	ldh [rWBK], a
	ld a, d
	ld [wPlusHUDLevel], a
	ld a, b
	ld [wPlusHUDGender], a
	ld a, c
	ld [wPlusHUDStatus], a
	push hl

	ld hl, wPlusHUDRow
	ld bc, wPlusHUDRowEnd - wPlusHUDRow
	xor a
	call ByteFill

	pop hl
	push hl
	call PlusHUDNameWidth
	ld d, a
	call PlusHUDTailWidth
	add d
	ld d, a
	; The name has a home: directly above the "P" of the "HP" label on the bar
	; below. It stays there whenever the rest of the row fits alongside it, so
	; the name starts in the same place from one mon to the next and the level
	; falls where it falls. Only a row too wide for that is set against the
	; right instead, which is what the Japanese one does too.
	ld a, PLUS_HUD_LEFT
	add d
	cp PLUS_HUD_ALIGN_TILES * TILE_WIDTH + 1
	ld a, PLUS_HUD_LEFT
	jr c, .fits

	ld a, PLUS_HUD_ALIGN_TILES * TILE_WIDTH
	sub d
	jr nc, .fits
	xor a ; wider than the row, so start at the left and run on
.fits
	ld [wPlusHUDX], a
	pop hl

.name
	ld a, [hli]
	cp '@'
	jr z, .name_done
	push hl
	call PlusHUDDrawGlyph
	pop hl
	jr .name

.name_done
	ld a, [wPlusHUDGender]
	and a
	jr z, .no_gender
	cp ' '
	jr z, .no_gender ; genderless
	ld b, a
	ld a, PLUS_HUD_GLYPH_MALE
	bit 1, b ; '♂' is $ef and '♀' is $f5, so bit 1 tells them apart
	jr nz, .got_symbol
	ld a, PLUS_HUD_GLYPH_FEMALE
.got_symbol
	call PlusHUDDrawIndex
.no_gender

	; the level, or the status condition in its place, the way vanilla does
	ld a, [wPlusHUDStatus]
	and a
	jr nz, .status
	call PlusHUDDrawLevel
	jr .done

.status
	ld c, a
	call PlusHUDDrawStatus

.done
; Report the tiles the row filled, so the caller knows how many to write.
	ld a, [wPlusHUDX]
	add 7 ; round up to a whole tile
	srl a
	srl a
	srl a
	ld b, a
	pop af
	ldh [rWBK], a
	ret

PlusHUDNameWidth:
; hl = '@' terminated name. Returns its width in pixels, preserving hl.
	push hl
	xor a
.loop
	ld d, a
	ld a, [hli]
	cp '@'
	ld a, d
	jr z, .done
	add PLUS_HUD_GLYPH_W
	jr .loop

.done
	pop hl
	ret

PlusHUDTailWidth:
; Returns in a the width in pixels of everything after the name, so the row
; can be measured before any of it is drawn. Preserves hl.
	ld a, [wPlusHUDGender]
	and a
	jr z, .no_gender
	cp ' '
	jr z, .no_gender
	ld a, TILE_WIDTH
	jr .got_gender

.no_gender
	xor a

.got_gender
	ld e, a

	; a status tag is three cells, and so is any level of ten or more, whether
	; that is ":L" and two digits or three digits on their own
	ld a, [wPlusHUDStatus]
	and a
	ld a, 3 * TILE_WIDTH
	jr nz, .got_tail
	ld a, [wPlusHUDLevel]
	cp 10
	ld a, 3 * TILE_WIDTH
	jr nc, .got_tail
	ld a, 2 * TILE_WIDTH ; ":L" and a single digit

.got_tail
	add e
	ret

PlusHUDStatusIndex:
; c = a non-zero status byte. Returns which of the five is showing, in the same
; order PlaceNonFaintStatus tests them, which is what decides the winner when a
; mon somehow has more than one.
	ld a, 1
	bit PSN, c
	ret nz
	ld a, 2
	bit BRN, c
	ret nz
	ld a, 3
	bit FRZ, c
	ret nz
	ld a, 4
	bit PAR, c
	ret nz
	xor a ; asleep
	ret

PlusHUDDrawStatus:
; c = a non-zero status byte. Draws its three tile tag where the level goes.
;
; A status draws as a tag rather than as letters: white on a black rounded bar,
; three cells wide, which is what a level takes too. Nothing in the palette
; changes to get white on black. Every battle background palette runs white to
; black, so art with its background filled and its letters knocked out of it
; comes out the right way round on its own.
	call PlusHUDStatusIndex
	ld l, a
	ld h, 0
	add hl, hl
	add hl, hl ; three glyphs a tag, rounded up to four for the shift
	ld de, .Tags
	add hl, de
	ld c, 3
.loop
	ld a, [hli]
	push hl
	push bc
	call PlusHUDDrawIndex
	pop bc
	pop hl
	dec c
	jr nz, .loop
	ret

.Tags:
; four bytes a row so the index can be shifted rather than multiplied; the
; fourth is never read
	db PLUS_HUD_TAG_SLP + 0, PLUS_HUD_TAG_SLP + 1, PLUS_HUD_TAG_SLP + 2, 0
	db PLUS_HUD_TAG_PSN + 0, PLUS_HUD_TAG_PSN + 1, PLUS_HUD_TAG_PSN + 2, 0
	db PLUS_HUD_TAG_BRN + 0, PLUS_HUD_TAG_BRN + 1, PLUS_HUD_TAG_BRN + 2, 0
	db PLUS_HUD_TAG_FRZ + 0, PLUS_HUD_TAG_FRZ + 1, PLUS_HUD_TAG_FRZ + 2, 0
	db PLUS_HUD_TAG_PAR + 0, PLUS_HUD_TAG_PAR + 1, PLUS_HUD_TAG_PAR + 2, 0

PlusHUDDrawLevel:
; ":L" and the level, in the game's own glyphs. A level of 100 fills all three
; cells with digits and drops the ":L", the way PrintLevel does.
	ld a, [wPlusHUDLevel]
	cp 100
	jr nc, .three_digits

	ld a, PLUS_HUD_GLYPH_LV
	call PlusHUDDrawIndex
	ld a, [wPlusHUDLevel]
	cp 10
	jr c, .ones ; a single digit gets no tens cell at all
	ld b, 10
	call .Digit
	jr .ones

.three_digits
; the hundreds digit cannot be zero here, and a zero after it is part of the
; number rather than a leading one, so every cell is drawn
	ld b, 100
	call .Digit
	ld b, 10
	call .Digit

.ones
	ld a, [wPlusHUDLevel]
	add PLUS_HUD_GLYPH_DIGIT
	jp PlusHUDDrawIndex

.Digit:
; b = place value. Draws that digit of wPlusHUDLevel and takes it off.
	ld a, [wPlusHUDLevel]
	ld c, 0
.count
	cp b
	jr c, .counted
	sub b
	inc c
	jr .count

.counted
	ld [wPlusHUDLevel], a
	ld a, c
	add PLUS_HUD_GLYPH_DIGIT
	jp PlusHUDDrawIndex

PlusHUDDrawGlyph:
; a = character. Draws it at the pen and moves the pen on.
	call PlusHUDGlyphIndex
	jr c, PlusHUDSkipGlyph
	; fallthrough

PlusHUDDrawIndex:
; a = glyph index. A glyph is five pixels wide, or eight for the ones copied
; from the game's own graphics, and tiles are eight, so most straddle two of
; them: each row is shifted into a sixteen bit pair and the halves are OR'd
; into the tile it starts in and the one after it.
	push af
	ld l, a
	ld h, 0
	add hl, hl
	add hl, hl
	add hl, hl
	ld bc, PlusHUDFont
	add hl, bc

	ld a, [wPlusHUDX]
	ld b, a
	and %00000111
	ld [wPlusHUDShift], a
	ld a, b
	and %11111000 ; the tile it starts in, times eight, is the byte offset
	ld e, a
	ld d, 0
	push hl
	ld hl, wPlusHUDRow
	add hl, de
	ld d, h
	ld e, l
	pop hl

	ld c, 8
.row
	ld a, [hli]
	push hl
	ld h, a
	ld l, 0
	ld a, [wPlusHUDShift]
	and a
	jr z, .shifted
	ld b, a
.shift
	srl h
	rr l
	dec b
	jr nz, .shift

.shifted
	ld a, [de]
	or h
	ld [de], a

	push de
	ld a, e
	add 8 ; the same row of the next tile
	ld e, a
	jr nc, .no_carry
	inc d
.no_carry
	ld a, [de]
	or l
	ld [de], a
	pop de

	inc de
	pop hl
	dec c
	jr nz, .row

	pop af
	cp PLUS_HUD_WIDE_FIRST
	ld a, PLUS_HUD_GLYPH_W
	jr c, .advance
	ld a, TILE_WIDTH ; the copied glyphs keep their original width

.advance
	ld b, a
	ld a, [wPlusHUDX]
	add b
	ld [wPlusHUDX], a
	ret

PlusHUDSkipGlyph:
; no glyph for this character, so leave a gap its width rather than closing up
	ld a, [wPlusHUDX]
	add PLUS_HUD_GLYPH_W
	ld [wPlusHUDX], a
	ret

PlusHUDGlyphIndex:
; a = character in, glyph index out. Carry set when there is no glyph.
	cp 'A'
	jr c, .not_upper
	cp 'Z' + 1
	jr nc, .not_upper
	sub 'A'
	ret

.not_upper
	cp 'a'
	jr c, .not_lower
	cp 'z' + 1
	jr nc, .not_lower
	sub 'a'
	add 26
	ret

.not_lower
	; '9' is $ff, so being at or above '0' is the whole test
	cp '0'
	jr c, .not_digit
	sub '0'
	add 52
	ret

.not_digit
	ld hl, .Others
.loop
	ld b, a
	ld a, [hli]
	and a
	jr z, .no_glyph
	cp b
	jr z, .found
	inc hl
	ld a, b
	jr .loop

.found
	ld a, [hl]
	ret

.no_glyph
	scf
	ret

.Others:
; character, glyph index. Terminated by a character of zero, which no text
; can contain.
	db ' ',  62
	db ':',  63
	db '.',  64
	db ',',  65
	db '-',  66
	db "'",  67
	db '!',  68
	db '?',  69
	db '/',  70
	db 0
