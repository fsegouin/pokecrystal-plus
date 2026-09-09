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
