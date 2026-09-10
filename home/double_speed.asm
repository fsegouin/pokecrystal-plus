; The CGB hardware introduces Double Speed Mode.
; While active, the clock speed is doubled.

; The hardware can switch between normal speed
; and double speed at any time, but LCD output
; collapses during the switch.

DoubleSpeed::
	ld hl, rSPD
	bit B_SPD_DOUBLE, [hl]
	jr z, SwitchSpeed
	ret

NormalSpeed::
	ld hl, rSPD
	bit B_SPD_DOUBLE, [hl]
	ret z

SwitchSpeed::
	set B_SPD_PREPARE, [hl]
	xor a
	ldh [rIF], a
	ldh [rIE], a
	ld a, JOYP_GET_NONE
	ldh [rJOYP], a
	stop ; rgbasm adds a nop after this instruction by default
	ret

; plus: the 60 fps overworld option runs the map loop once per frame instead
; of once every two, and the iteration that rebuilds the on-screen tilemap
; does not fit in a single frame at normal CPU speed. Double speed halves the
; cost of that iteration so it does fit.
;
; Both entry points below are safe to call from anywhere: they compare the
; wanted speed against the current one and return without doing anything when
; the two already agree, so the LCD only blanks on a real change.

PlusUpdateOverworldSpeed::
; Match the CPU speed to the frame rate option. Called from the overworld
; loop, so a toggle in the options menu takes effect on the next iteration.
	push af
	push hl
	ldh a, [hCGB]
	and a
	jr z, .done
	ld a, [wOptions2]
	bit FRAME_RATE_60_F, a
	ld hl, rSPD
	jr z, .want_normal
	bit B_SPD_DOUBLE, [hl]
	call z, PlusSwitchSpeed
	jr .done

.want_normal
	bit B_SPD_DOUBLE, [hl]
	call nz, PlusSwitchSpeed

.done
	pop hl
	pop af
	ret

PlusNormalSpeed::
; Drop back to normal speed before anything whose timing comes from the CPU
; clock rather than from VBlank: battles, saving, and every serial transfer.
; Preserves every register, since some of the callers are byte loops.
	push af
	push hl
	ldh a, [hCGB]
	and a
	jr z, .done
	ld hl, rSPD
	bit B_SPD_DOUBLE, [hl]
	call nz, PlusSwitchSpeed

.done
	pop hl
	pop af
	ret

PlusSwitchSpeed:
; SwitchSpeed clears rIE and never puts it back; its callers in vanilla write
; it again themselves. These callers cannot, since they run at any point in
; the game, so keep whatever was enabled and restore it afterwards. hl already
; points at rSPD, which is what SwitchSpeed expects.
	di
	ldh a, [rIE]
	push af
	call SwitchSpeed
	pop af
	ldh [rIE], a
	ei
	ret
