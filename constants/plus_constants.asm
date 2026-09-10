; Pokémon Crystal+ constants
; See docs/plus.md for the feature overview and hook registry.

; wPlusFlags::
	const_def
	const PLUS_WILD_ENABLED_F ; 0
	const PLUS_WILD_MODE_LO_F ; 1
	const PLUS_WILD_MODE_HI_F ; 2
	const PLUS_TRAINERS_F     ; 3
	const PLUS_EXP_BOOST_F    ; 4

DEF PLUS_WILD_MODE_MASK  EQU (1 << PLUS_WILD_MODE_LO_F) | (1 << PLUS_WILD_MODE_HI_F)
DEF PLUS_WILD_MODE_SHIFT EQU PLUS_WILD_MODE_LO_F

; wild randomizer modes (stored in wPlusFlags bits 1-2)
	const_def
	const PLUS_WILD_MODE_TIERED   ; 0 - permute within each BST tier
	const PLUS_WILD_MODE_UNTIERED ; 1 - permute across all tiers as one list
	const PLUS_WILD_MODE_CHAOS    ; 2 - fresh roll per encounter, no permutation
DEF NUM_PLUS_WILD_MODES EQU const_value

; PlusSetWildMode takes a mode in wScriptVar, or this to switch the wild
; randomizer off. Any value at or above NUM_PLUS_WILD_MODES turns it off.
DEF PLUS_WILD_SET_OFF EQU NUM_PLUS_WILD_MODES

; PlusMapStarterMon slots, in the order the poke balls sit on Elm's table
	const_def
	const PLUS_STARTER_LEFT   ; 0 - Cyndaquil's ball
	const PLUS_STARTER_MIDDLE ; 1 - Totodile's ball
	const PLUS_STARTER_RIGHT  ; 2 - Chikorita's ball
DEF NUM_PLUS_STARTERS EQU const_value
