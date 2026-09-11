LoadBattleMenu:
	ld hl, BattleMenuHeader
	call LoadMenuHeader
	ld a, [wBattleMenuCursorPosition]
	ld [wMenuCursorPosition], a
.loop ; plus
	call InterpretBattleMenu
	call PlusBattleMenuB ; plus: B puts the cursor on RUN rather than choosing
	jr c, .loop ; plus
	ld a, [wMenuCursorPosition]
	ld [wBattleMenuCursorPosition], a
	call ExitMenu
	ret

SafariBattleMenu: ; unreferenced
	ld hl, SafariBattleMenuHeader
	call LoadMenuHeader
	jr CommonBattleMenu

ContestBattleMenu:
	ld hl, ContestBattleMenuHeader
	call LoadMenuHeader
	; fallthrough

CommonBattleMenu:
	ld a, [wBattleMenuCursorPosition]
	ld [wMenuCursorPosition], a
.loop ; plus
	call _2DMenu
	call PlusBattleMenuB ; plus
	jr c, .loop ; plus
	ld a, [wMenuCursorPosition]
	ld [wBattleMenuCursorPosition], a
	call ExitMenu
	ret

PlusBattleMenuB: ; plus
; B leaves the menu with nothing chosen. Put the cursor on RUN, the bottom
; right option in the battle and Bug Contest menus alike, and return carry so
; the caller shows the menu again. Any other way out returns no carry.
	call GetMenuJoypad
	and PAD_A | PAD_B
	cp PAD_B
	jr nz, .chosen
	ld a, 4 ; RUN
	ld [wMenuCursorPosition], a
	scf
	ret

.chosen
	and a
	ret

BattleMenuHeader:
	db MENU_BACKUP_TILES ; flags
	menu_coords 8, 12, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1
	dw .MenuData
	db 1 ; default option

.MenuData:
	db STATICMENU_CURSOR ; flags ; plus: B allowed, for PlusBattleMenuB
	dn 2, 2 ; rows, columns
	db 6 ; spacing
	dba .Text
	dbw BANK(@), NULL

.Text:
	db "FIGHT@"
	db "<PKMN>@"
	db "PACK@"
	db "RUN@"

SafariBattleMenuHeader:
	db MENU_BACKUP_TILES ; flags
	menu_coords 0, 12, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1
	dw .MenuData
	db 1 ; default option

.MenuData:
	db STATICMENU_CURSOR | STATICMENU_DISABLE_B ; flags
	dn 2, 2 ; rows, columns
	db 11 ; spacing
	dba .Text
	dba .PrintSafariBallsRemaining

.Text:
	db "サファりボール×　　@" ; "SAFARI BALL×  @"
	db "エサをなげる@" ; "THROW BAIT"
	db "いしをなげる@" ; "THROW ROCK"
	db "にげる@" ; "RUN"

.PrintSafariBallsRemaining:
	hlcoord 17, 13
	ld de, wSafariBallsRemaining
	lb bc, PRINTNUM_LEADINGZEROS | 1, 2
	call PrintNum
	ret

ContestBattleMenuHeader:
	db MENU_BACKUP_TILES ; flags
	menu_coords 2, 12, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1
	dw .MenuData
	db 1 ; default option

.MenuData:
	db STATICMENU_CURSOR ; flags ; plus: B allowed, for PlusBattleMenuB
	dn 2, 2 ; rows, columns
	db 12 ; spacing
	dba .Text
	dba .PrintParkBallsRemaining

.Text:
	db "FIGHT@"
	db "<PKMN>@"
	db "PARKBALL×  @"
	db "RUN@"

.PrintParkBallsRemaining:
	hlcoord 13, 16
	ld de, wParkBallsRemaining
	lb bc, PRINTNUM_LEADINGZEROS | 1, 2
	call PrintNum
	ret
