; GetOptionPointer.Pointers indexes
	const_def
	const OPT_TEXT_SPEED    ; 0
	const OPT_BATTLE_SCENE  ; 1
	const OPT_BATTLE_STYLE  ; 2
	const OPT_SOUND         ; 3
	const OPT_PRINT         ; 4
	const OPT_MENU_ACCOUNT  ; 5
	const OPT_FRAME         ; 6
	const OPT_CANCEL        ; 7
DEF NUM_OPTIONS EQU const_value ; 8

; plus: the eight rows above fill the screen, so anything new goes on a second
; page reached with SELECT. GetOptionPointer.PlusPointers indexes.
	const_def
	const PLUS_OPT_FRAME_RATE ; 0
	const PLUS_OPT_CANCEL     ; 1
DEF NUM_PLUS_OPTIONS EQU const_value ; 2

DEF OPTIONS_PAGE_MAIN EQU 0
DEF OPTIONS_PAGE_PLUS EQU 1

_Option:
; BUG: Options menu fails to clear joypad state on initialization (see docs/bugs_and_glitches.md)
	ld hl, hInMenu
	ld a, [hl]
	push af
	ld [hl], TRUE
	call ClearBGPalettes
	ld a, OPTIONS_PAGE_MAIN ; plus: always open on the familiar page
	ld [wPlusOptionsPage], a
	call Options_DrawPage
	ld b, SCGB_DIPLOMA
	call GetSGBLayout
	call SetDefaultBGPAndOBP

.joypad_loop
	call JoyTextDelay
	ldh a, [hJoyPressed]
	and PAD_START | PAD_B
	jr nz, .ExitOptions
	ldh a, [hJoyPressed] ; plus
	and PAD_SELECT
	jr nz, .SwitchPage
	call OptionsControl
	jr c, .dpad
	call GetOptionPointer
	jr c, .ExitOptions

.dpad
	call Options_UpdateCursorPosition
	ld c, 3
	call DelayFrames
	jr .joypad_loop

.SwitchPage: ; plus
	ld hl, wPlusOptionsPage
	ld a, [hl]
	xor OPTIONS_PAGE_PLUS
	ld [hl], a
	ld de, SFX_READ_TEXT_2
	call PlaySFX
	call Options_DrawPage
	jr .joypad_loop

.ExitOptions:
	ld de, SFX_TRANSACTION
	call PlaySFX
	call WaitSFX
	pop af
	ldh [hInMenu], a
	ret

; plus: draw the current page from scratch, cursor and current values and all.
; Run once when the menu opens and again on every SELECT.
Options_DrawPage:
	xor a
	ldh [hBGMapMode], a
	hlcoord 0, 0
	ld b, SCREEN_HEIGHT - 2
	ld c, SCREEN_WIDTH - 2
	call Textbox
	hlcoord 2, 2
	ld a, [wPlusOptionsPage]
	and a
	jr nz, .plus_page
	ld de, StringOptions
	call PlaceString
	xor a
	ld [wJumptableIndex], a
; display the settings of each option when the menu is opened
	ld c, NUM_OPTIONS - 2 ; omit frame type, the last option
	call .print_values
	call UpdateFrame ; display the frame type
	jr .drawn

.plus_page
	ld de, StringPlusOptions
	call PlaceString
	xor a
	ld [wJumptableIndex], a
	ld c, NUM_PLUS_OPTIONS - 1 ; omit CANCEL, which has nothing to show
	call .print_values

.drawn
	xor a
	ld [wJumptableIndex], a
	call Options_UpdateCursorPosition
	ld a, 1
	ldh [hBGMapMode], a
	call WaitBGMap
	ret

.print_values
	push bc
	xor a
	ldh [hJoyLast], a
	call GetOptionPointer
	pop bc
	ld hl, wJumptableIndex
	inc [hl]
	dec c
	jr nz, .print_values
	ret

StringOptions:
	db "TEXT SPEED<LF>"
	db "        :<LF>"
	db "BATTLE SCENE<LF>"
	db "        :<LF>"
	db "BATTLE STYLE<LF>"
	db "        :<LF>"
	db "SOUND<LF>"
	db "        :<LF>"
	db "PRINT<LF>"
	db "        :<LF>"
	db "MENU ACCOUNT<LF>"
	db "        :<LF>"
	db "FRAME<LF>"
	db "        :TYPE<LF>"
	db "CANCEL@"

; plus: the SELECT page
StringPlusOptions:
	db "FRAME RATE<LF>"
	db "        :<LF>"
	db "CANCEL@"

GetOptionPointer:
	ld a, [wPlusOptionsPage] ; plus
	and a
	jr nz, .plus_page
	jumptable .Pointers, wJumptableIndex

.plus_page ; plus
	jumptable .PlusPointers, wJumptableIndex

.Pointers:
; entries correspond to OPT_* constants
	dw Options_TextSpeed
	dw Options_BattleScene
	dw Options_BattleStyle
	dw Options_Sound
	dw Options_Print
	dw Options_MenuAccount
	dw Options_Frame
	dw Options_Cancel

.PlusPointers: ; plus
; entries correspond to PLUS_OPT_* constants
	dw Options_FrameRate
	dw Options_Cancel

; plus: INST heads the list so LEFT still means faster and RIGHT slower
	const_def
	const OPT_TEXT_SPEED_INST ; 0
	const OPT_TEXT_SPEED_FAST ; 1
	const OPT_TEXT_SPEED_MED  ; 2
	const OPT_TEXT_SPEED_SLOW ; 3

Options_TextSpeed:
	call GetTextSpeed
	ldh a, [hJoyPressed]
	bit B_PAD_LEFT, a
	jr nz, .LeftPressed
	bit B_PAD_RIGHT, a
	jr z, .NonePressed
	ld a, c ; right pressed
	cp OPT_TEXT_SPEED_SLOW
	jr c, .Increase
	ld c, OPT_TEXT_SPEED_INST - 1 ; plus: INST is now the first entry

.Increase:
	inc c
	ld a, e
	jr .Save

.LeftPressed:
	ld a, c
	and a
	jr nz, .Decrease
	ld c, OPT_TEXT_SPEED_SLOW + 1

.Decrease:
	dec c
	ld a, d

.Save:
	ld b, a
	ld a, [wOptions]
	and $f0
	or b
	ld [wOptions], a

.NonePressed:
	ld b, 0
	ld hl, .Strings
	add hl, bc
	add hl, bc
	ld e, [hl]
	inc hl
	ld d, [hl]
	hlcoord 11, 3
	call PlaceString
	and a
	ret

.Strings:
; entries correspond to OPT_TEXT_SPEED_* constants
	dw .Inst ; plus
	dw .Fast
	dw .Mid
	dw .Slow

.Inst: db "INST@" ; plus
.Fast: db "FAST@"
.Mid:  db "MID @"
.Slow: db "SLOW@"

GetTextSpeed:
; converts TEXT_DELAY_* value in a to OPT_TEXT_SPEED_* value in c,
; with previous/next TEXT_DELAY_* values in d/e
	ld a, [wOptions]
	and TEXT_DELAY_MASK
	cp TEXT_DELAY_INST ; plus
	jr z, .inst ; plus
	cp TEXT_DELAY_SLOW
	jr z, .slow
	cp TEXT_DELAY_FAST
	jr z, .fast
	; none of the above
	ld c, OPT_TEXT_SPEED_MED
	lb de, TEXT_DELAY_FAST, TEXT_DELAY_SLOW
	ret

.slow
	ld c, OPT_TEXT_SPEED_SLOW
	lb de, TEXT_DELAY_MED, TEXT_DELAY_INST ; plus: SLOW is last, so RIGHT wraps to INST
	ret

.fast
	ld c, OPT_TEXT_SPEED_FAST
	lb de, TEXT_DELAY_INST, TEXT_DELAY_MED ; plus: LEFT from FAST reaches INST
	ret

; plus: INST is first, so LEFT wraps round to SLOW
.inst
	ld c, OPT_TEXT_SPEED_INST
	lb de, TEXT_DELAY_SLOW, TEXT_DELAY_FAST
	ret

Options_BattleScene:
	ld hl, wOptions
	ldh a, [hJoyPressed]
	bit B_PAD_LEFT, a
	jr nz, .LeftPressed
	bit B_PAD_RIGHT, a
	jr z, .NonePressed
	bit BATTLE_SCENE, [hl]
	jr nz, .ToggleOn
	jr .ToggleOff

.LeftPressed:
	bit BATTLE_SCENE, [hl]
	jr z, .ToggleOff
	jr .ToggleOn

.NonePressed:
	bit BATTLE_SCENE, [hl]
	jr z, .ToggleOn
	jr .ToggleOff

.ToggleOn:
	res BATTLE_SCENE, [hl]
	ld de, .On
	jr .Display

.ToggleOff:
	set BATTLE_SCENE, [hl]
	ld de, .Off

.Display:
	hlcoord 11, 5
	call PlaceString
	and a
	ret

.On:  db "ON @"
.Off: db "OFF@"

Options_BattleStyle:
	ld hl, wOptions
	ldh a, [hJoyPressed]
	bit B_PAD_LEFT, a
	jr nz, .LeftPressed
	bit B_PAD_RIGHT, a
	jr z, .NonePressed
	bit BATTLE_SHIFT, [hl]
	jr nz, .ToggleShift
	jr .ToggleSet

.LeftPressed:
	bit BATTLE_SHIFT, [hl]
	jr z, .ToggleSet
	jr .ToggleShift

.NonePressed:
	bit BATTLE_SHIFT, [hl]
	jr nz, .ToggleSet

.ToggleShift:
	res BATTLE_SHIFT, [hl]
	ld de, .Shift
	jr .Display

.ToggleSet:
	set BATTLE_SHIFT, [hl]
	ld de, .Set

.Display:
	hlcoord 11, 7
	call PlaceString
	and a
	ret

.Shift: db "SHIFT@"
.Set:   db "SET  @"

Options_Sound:
	ld hl, wOptions
	ldh a, [hJoyPressed]
	bit B_PAD_LEFT, a
	jr nz, .LeftPressed
	bit B_PAD_RIGHT, a
	jr z, .NonePressed
	bit STEREO, [hl]
	jr nz, .SetMono
	jr .SetStereo

.LeftPressed:
	bit STEREO, [hl]
	jr z, .SetStereo
	jr .SetMono

.NonePressed:
	bit STEREO, [hl]
	jr nz, .ToggleStereo
	jr .ToggleMono

.SetMono:
	res STEREO, [hl]
	call RestartMapMusic

.ToggleMono:
	ld de, .Mono
	jr .Display

.SetStereo:
	set STEREO, [hl]
	call RestartMapMusic

.ToggleStereo:
	ld de, .Stereo

.Display:
	hlcoord 11, 9
	call PlaceString
	and a
	ret

.Mono:   db "MONO  @"
.Stereo: db "STEREO@"

	const_def
	const OPT_PRINT_LIGHTEST ; 0
	const OPT_PRINT_LIGHTER  ; 1
	const OPT_PRINT_NORMAL   ; 2
	const OPT_PRINT_DARKER   ; 3
	const OPT_PRINT_DARKEST  ; 4

Options_Print:
	call GetPrinterSetting
	ldh a, [hJoyPressed]
	bit B_PAD_LEFT, a
	jr nz, .LeftPressed
	bit B_PAD_RIGHT, a
	jr z, .NonePressed
	ld a, c
	cp OPT_PRINT_DARKEST
	jr c, .Increase
	ld c, OPT_PRINT_LIGHTEST - 1

.Increase:
	inc c
	ld a, e
	jr .Save

.LeftPressed:
	ld a, c
	and a
	jr nz, .Decrease
	ld c, OPT_PRINT_DARKEST + 1

.Decrease:
	dec c
	ld a, d

.Save:
	ld b, a
	ld [wGBPrinterBrightness], a

.NonePressed:
	ld b, 0
	ld hl, .Strings
	add hl, bc
	add hl, bc
	ld e, [hl]
	inc hl
	ld d, [hl]
	hlcoord 11, 11
	call PlaceString
	and a
	ret

.Strings:
; entries correspond to OPT_PRINT_* constants
	dw .Lightest
	dw .Lighter
	dw .Normal
	dw .Darker
	dw .Darkest

.Lightest: db "LIGHTEST@"
.Lighter:  db "LIGHTER @"
.Normal:   db "NORMAL  @"
.Darker:   db "DARKER  @"
.Darkest:  db "DARKEST @"

GetPrinterSetting:
; converts GBPRINTER_* value in a to OPT_PRINT_* value in c,
; with previous/next GBPRINTER_* values in d/e
	ld a, [wGBPrinterBrightness]
	and a
	jr z, .IsLightest
	cp GBPRINTER_LIGHTER
	jr z, .IsLight
	cp GBPRINTER_DARKER
	jr z, .IsDark
	cp GBPRINTER_DARKEST
	jr z, .IsDarkest
	; none of the above
	ld c, OPT_PRINT_NORMAL
	lb de, GBPRINTER_LIGHTER, GBPRINTER_DARKER
	ret

.IsLightest:
	ld c, OPT_PRINT_LIGHTEST
	lb de, GBPRINTER_DARKEST, GBPRINTER_LIGHTER
	ret

.IsLight:
	ld c, OPT_PRINT_LIGHTER
	lb de, GBPRINTER_LIGHTEST, GBPRINTER_NORMAL
	ret

.IsDark:
	ld c, OPT_PRINT_DARKER
	lb de, GBPRINTER_NORMAL, GBPRINTER_DARKEST
	ret

.IsDarkest:
	ld c, OPT_PRINT_DARKEST
	lb de, GBPRINTER_DARKER, GBPRINTER_LIGHTEST
	ret

Options_MenuAccount:
	ld hl, wOptions2
	ldh a, [hJoyPressed]
	bit B_PAD_LEFT, a
	jr nz, .LeftPressed
	bit B_PAD_RIGHT, a
	jr z, .NonePressed
	bit MENU_ACCOUNT, [hl]
	jr nz, .ToggleOff
	jr .ToggleOn

.LeftPressed:
	bit MENU_ACCOUNT, [hl]
	jr z, .ToggleOn
	jr .ToggleOff

.NonePressed:
	bit MENU_ACCOUNT, [hl]
	jr nz, .ToggleOn

.ToggleOff:
	res MENU_ACCOUNT, [hl]
	ld de, .Off
	jr .Display

.ToggleOn:
	set MENU_ACCOUNT, [hl]
	ld de, .On

.Display:
	hlcoord 11, 13
	call PlaceString
	and a
	ret

.Off: db "OFF@"
.On:  db "ON @"

; plus: 30 runs the overworld loop every other frame, as the game always has;
; 60 runs it every frame with half-size steps, so walking takes the same time
; but the screen scrolls a pixel at a time instead of two. Only bit
; FRAME_RATE_60_F is touched, leaving MENU_ACCOUNT beside it alone.
Options_FrameRate:
	ld hl, wOptions2
	ldh a, [hJoyPressed]
	bit B_PAD_LEFT, a
	jr nz, .LeftPressed
	bit B_PAD_RIGHT, a
	jr z, .NonePressed
	bit FRAME_RATE_60_F, [hl]
	jr nz, .Set30
	jr .Set60

.LeftPressed:
	bit FRAME_RATE_60_F, [hl]
	jr z, .Set60
	jr .Set30

.NonePressed:
	bit FRAME_RATE_60_F, [hl]
	jr nz, .Set60

.Set30:
	res FRAME_RATE_60_F, [hl]
	ld de, .Thirty
	jr .Display

.Set60:
	set FRAME_RATE_60_F, [hl]
	ld de, .Sixty

.Display:
	hlcoord 11, 3
	call PlaceString
	and a
	ret

.Thirty: db "30@"
.Sixty:  db "60@"

Options_Frame:
	ld hl, wTextboxFrame
	ldh a, [hJoyPressed]
	bit B_PAD_LEFT, a
	jr nz, .LeftPressed
	bit B_PAD_RIGHT, a
	jr nz, .RightPressed
	and a
	ret

.RightPressed:
	ld a, [hl]
	inc a
	jr .Save

.LeftPressed:
	ld a, [hl]
	dec a

.Save:
	maskbits NUM_FRAMES
	ld [hl], a
UpdateFrame:
	ld a, [wTextboxFrame]
	hlcoord 16, 15 ; where on the screen the number is drawn
	add '1'
	ld [hl], a
	call LoadFontsExtra
	and a
	ret

Options_Cancel:
	ldh a, [hJoyPressed]
	and PAD_A
	jr nz, .Exit
	and a
	ret

.Exit:
	scf
	ret

OptionsControl:
	ld hl, wJumptableIndex
	ldh a, [hJoyLast]
	cp PAD_DOWN
	jr z, .DownPressed
	cp PAD_UP
	jr z, .UpPressed
	and a
	ret

; plus: the second page has two entries, so up and down both just flip between
; them. PLUS_OPT_CANCEL is 1, so xor with it toggles.
.PlusPage:
	ld a, [hl]
	xor PLUS_OPT_CANCEL
	ld [hl], a
	scf
	ret

.DownPressed:
	ld a, [wPlusOptionsPage] ; plus
	and a
	jr nz, .PlusPage
	ld a, [hl]
	cp OPT_CANCEL ; maximum option index
	jr nz, .CheckMenuAccount
	ld [hl], OPT_TEXT_SPEED ; first option
	scf
	ret

.CheckMenuAccount: ; I have no idea why this exists...
	cp OPT_MENU_ACCOUNT
	jr nz, .Increase
	ld [hl], OPT_MENU_ACCOUNT

.Increase:
	inc [hl]
	scf
	ret

.UpPressed:
	ld a, [wPlusOptionsPage] ; plus
	and a
	jr nz, .PlusPage
	ld a, [hl]

; Another thing where I'm not sure why it exists
	cp OPT_FRAME
	jr nz, .NotFrame
	ld [hl], OPT_MENU_ACCOUNT
	scf
	ret

.NotFrame:
	and a ; OPT_TEXT_SPEED, minimum option index
	jr nz, .Decrease
	ld [hl], NUM_OPTIONS ; decrements to OPT_CANCEL, maximum option index

.Decrease:
	dec [hl]
	scf
	ret

Options_UpdateCursorPosition:
	hlcoord 1, 1
	ld de, SCREEN_WIDTH
	ld c, SCREEN_HEIGHT - 2
.loop
	ld [hl], ' '
	add hl, de
	dec c
	jr nz, .loop
	hlcoord 1, 2
	ld bc, 2 * SCREEN_WIDTH
	ld a, [wJumptableIndex]
	call AddNTimes
	ld [hl], '▶'
	ret
