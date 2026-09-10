; Species PLUS_WILD_MODE_CHAOS refuses to roll.
;
; Chaos picks a fresh species from the whole dex on every encounter, so the
; only thing stopping a level 3 Route 29 Mewtwo is this list. The eleven
; legendaries stay where their own scripts put them, and Unown stays inside
; the Ruins of Alph so its puzzles and its printer still work.
;
; The shuffle modes do not need this list: their pool is PlusTierC through
; PlusTierA, which never contained these species in the first place.

PlusChaosBans:
	db ARTICUNO
	db ZAPDOS
	db MOLTRES
	db MEWTWO
	db MEW
	db RAIKOU
	db ENTEI
	db SUICUNE
	db LUGIA
	db HO_OH
	db CELEBI
	db UNOWN
	db -1 ; end
