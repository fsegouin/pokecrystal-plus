; Wild encounter randomizer - species tiers
;
; Generated from base_stats + evos_attacks (BST bands C < 385 <= B < 460 <= A),
; then hand-adjusted where base stat total misrepresents a species:
;   SHUCKLE   A -> B   10 Atk / 10 SpA; 505 BST is all defence, cannot attack
;   CHANSEY   B -> A   450 BST is almost entirely HP
;   WOBBUFFET B -> C   movepool is Counter/Mirror Coat/Safeguard/Destiny Bond
;                      - no damaging move at any level
;   ONIX      B -> C   385 BST is one inflated stat, 35 HP
;   CORSOLA   C -> B   never evolves; was already at C's ceiling
;   AIPOM     C -> B   never evolves; was already at C's ceiling
;
; Sizes 95/44/27.
;
; POOL (166 species): everything with a wild source in vanilla Crystal
; (grass, water, swarms, fishing, headbutt/rock smash, bug contest) plus
; Game Corner prize mons, the three starters and sixteen species with no
; vanilla source at all, minus the 11 legendaries and Unown.
;
; The pool is a permutation domain. Sixteen of the species added to the pool
; have no vanilla slot of their own, so each run leaves sixteen pool species
; with no source, varying by seed. The other 73 species have no wild source
; in vanilla either, so nothing is lost there.
;
; PLUS_WILD_MODE_TIERED   - permute within each of A / B / C separately
; PLUS_WILD_MODE_UNTIERED - permute across all three as one list
; PLUS_WILD_MODE_CHAOS    - ignores these lists entirely; rolls from all 239
;                           allowed species per encounter. Not a permutation,
;                           so Pokedex AREA falls back to vanilla behaviour.
;
; PlusTierC falls through into PlusTierStarter. Before EVENT_GOT_STARTER is
; set, the starter slots shuffle over PlusTierStarter alone, so your starter
; is always a mon that can still evolve.
;
; NOTE: Abra, Cubone, Magikarp, Ditto, Igglybuff, Hoppip and Smeargle are in
; C tier but NOT starter-legal - none of them can deal damage at level 5,
; which would make the first rival battle unwinnable. Igglybuff is the near
; miss: Sing, Charm and Defense Curl by level 4, but Pound not until 9.

PlusTierC:
	db METAPOD      ;  11  BST 205  stage 1
	db KAKUNA       ;  14  BST 205  stage 1
	db PIDGEOTTO    ;  17  BST 349  stage 1
	db NIDORINA     ;  30  BST 365  stage 1
	db NIDORINO     ;  33  BST 365  stage 1
	db CLEFAIRY     ;  35  BST 323  stage 1
	db JIGGLYPUFF   ;  39  BST 270  stage 1
	db ABRA         ;  63  BST 310  stage 0
	db FARFETCH_D   ;  83  BST 352  stage 0
	db ONIX         ;  95  BST 385  stage 0
	db CUBONE       ; 104  BST 320  stage 0
	db RHYHORN      ; 111  BST 345  stage 0
	db MAGIKARP     ; 129  BST 200  stage 0
	db DITTO        ; 132  BST 288  stage 0
	db IGGLYBUFF    ; 174  BST 210  stage 0
	db HOPPIP       ; 187  BST 250  stage 0
	db SKIPLOOM     ; 188  BST 340  stage 1
	db WOBBUFFET    ; 202  BST 405  stage 0
	db SMEARGLE     ; 235  BST 250  stage 0
	; fallthrough
PlusTierStarter:
	db BULBASAUR    ;   1  BST 318  stage 0
	db CHARMANDER   ;   4  BST 309  stage 0
	db SQUIRTLE     ;   7  BST 314  stage 0
	db CATERPIE     ;  10  BST 195  stage 0
	db WEEDLE       ;  13  BST 195  stage 0
	db PIDGEY       ;  16  BST 251  stage 0
	db RATTATA      ;  19  BST 253  stage 0
	db SPEAROW      ;  21  BST 262  stage 0
	db EKANS        ;  23  BST 288  stage 0
	db PIKACHU      ;  25  BST 300  stage 1
	db SANDSHREW    ;  27  BST 300  stage 0
	db NIDORAN_F    ;  29  BST 275  stage 0
	db NIDORAN_M    ;  32  BST 273  stage 0
	db VULPIX       ;  37  BST 299  stage 0
	db ZUBAT        ;  41  BST 245  stage 0
	db ODDISH       ;  43  BST 320  stage 0
	db PARAS        ;  46  BST 285  stage 0
	db VENONAT      ;  48  BST 305  stage 0
	db DIGLETT      ;  50  BST 265  stage 0
	db MEOWTH       ;  52  BST 290  stage 0
	db PSYDUCK      ;  54  BST 320  stage 0
	db MANKEY       ;  56  BST 305  stage 0
	db GROWLITHE    ;  58  BST 350  stage 0
	db POLIWAG      ;  60  BST 300  stage 0
	db MACHOP       ;  66  BST 305  stage 0
	db BELLSPROUT   ;  69  BST 300  stage 0
	db TENTACOOL    ;  72  BST 335  stage 0
	db GEODUDE      ;  74  BST 300  stage 0
	db SLOWPOKE     ;  79  BST 315  stage 0
	db MAGNEMITE    ;  81  BST 325  stage 0
	db DODUO        ;  84  BST 310  stage 0
	db SEEL         ;  86  BST 325  stage 0
	db GRIMER       ;  88  BST 325  stage 0
	db SHELLDER     ;  90  BST 305  stage 0
	db GASTLY       ;  92  BST 310  stage 0
	db DROWZEE      ;  96  BST 328  stage 0
	db KRABBY       ;  98  BST 325  stage 0
	db VOLTORB      ; 100  BST 330  stage 0
	db EXEGGCUTE    ; 102  BST 325  stage 0
	db KOFFING      ; 109  BST 340  stage 0
	db HORSEA       ; 116  BST 295  stage 0
	db GOLDEEN      ; 118  BST 320  stage 0
	db STARYU       ; 120  BST 340  stage 0
	db EEVEE        ; 133  BST 325  stage 0
	db OMANYTE      ; 138  BST 355  stage 0
	db KABUTO       ; 140  BST 355  stage 0
	db DRATINI      ; 147  BST 300  stage 0
	db CHIKORITA    ; 152  BST 318  stage 0
	db CYNDAQUIL    ; 155  BST 309  stage 0
	db TOTODILE     ; 158  BST 314  stage 0
	db SENTRET      ; 161  BST 215  stage 0
	db HOOTHOOT     ; 163  BST 262  stage 0
	db LEDYBA       ; 165  BST 265  stage 0
	db SPINARAK     ; 167  BST 250  stage 0
	db CHINCHOU     ; 170  BST 330  stage 0
	db PICHU        ; 172  BST 205  stage 0
	db CLEFFA       ; 173  BST 218  stage 0
	db NATU         ; 177  BST 320  stage 0
	db MAREEP       ; 179  BST 280  stage 0
	db MARILL       ; 183  BST 250  stage 0
	db SUNKERN      ; 191  BST 180  stage 0
	db WOOPER       ; 194  BST 210  stage 0
	db PINECO       ; 204  BST 290  stage 0
	db SNUBBULL     ; 209  BST 300  stage 0
	db TEDDIURSA    ; 216  BST 330  stage 0
	db SLUGMA       ; 218  BST 250  stage 0
	db SWINUB       ; 220  BST 250  stage 0
	db REMORAID     ; 223  BST 300  stage 0
	db DELIBIRD     ; 225  BST 330  stage 0
	db HOUNDOUR     ; 228  BST 330  stage 0
	db PHANPY       ; 231  BST 330  stage 0
	db TYROGUE      ; 236  BST 210  stage 0
	db SMOOCHUM     ; 238  BST 305  stage 0
	db ELEKID       ; 239  BST 360  stage 0
	db MAGBY        ; 240  BST 365  stage 0
	db LARVITAR     ; 246  BST 300  stage 0
	db -1 ; end

PlusTierB:
	db BUTTERFREE   ;  12  BST 385  stage 2
	db BEEDRILL     ;  15  BST 385  stage 2
	db RATICATE     ;  20  BST 413  stage 1
	db FEAROW       ;  22  BST 442  stage 1
	db ARBOK        ;  24  BST 438  stage 1
	db SANDSLASH    ;  28  BST 450  stage 1
	db GOLBAT       ;  42  BST 455  stage 1
	db GLOOM        ;  44  BST 395  stage 1
	db PARASECT     ;  47  BST 405  stage 1
	db VENOMOTH     ;  49  BST 450  stage 1
	db DUGTRIO      ;  51  BST 405  stage 1
	db PERSIAN      ;  53  BST 440  stage 1
	db POLIWHIRL    ;  61  BST 385  stage 1
	db KADABRA      ;  64  BST 400  stage 1
	db MACHOKE      ;  67  BST 405  stage 1
	db WEEPINBELL   ;  70  BST 390  stage 1
	db GRAVELER     ;  75  BST 390  stage 1
	db PONYTA       ;  77  BST 410  stage 0
	db HAUNTER      ;  93  BST 405  stage 1
	db MAROWAK      ; 105  BST 425  stage 1
	db LICKITUNG    ; 108  BST 385  stage 0
	db TANGELA      ; 114  BST 435  stage 0
	db SEADRA       ; 117  BST 440  stage 1
	db SEAKING      ; 119  BST 450  stage 1
	db JYNX         ; 124  BST 455  stage 1
	db PORYGON      ; 137  BST 395  stage 0
	db DRAGONAIR    ; 148  BST 420  stage 1
	db FURRET       ; 162  BST 415  stage 1
	db NOCTOWL      ; 164  BST 442  stage 1
	db LEDIAN       ; 166  BST 390  stage 1
	db ARIADOS      ; 168  BST 390  stage 1
	db AIPOM        ; 190  BST 360  stage 0
	db YANMA        ; 193  BST 390  stage 0
	db QUAGSIRE     ; 195  BST 430  stage 1
	db MURKROW      ; 198  BST 405  stage 0
	db MISDREAVUS   ; 200  BST 435  stage 0
	db DUNSPARCE    ; 206  BST 415  stage 0
	db GLIGAR       ; 207  BST 430  stage 0
	db GRANBULL     ; 210  BST 450  stage 1
	db QWILFISH     ; 211  BST 430  stage 0
	db SHUCKLE      ; 213  BST 505  stage 0
	db SNEASEL      ; 215  BST 430  stage 0
	db CORSOLA      ; 222  BST 380  stage 0
	db PUPITAR      ; 247  BST 410  stage 1
	db -1 ; end

PlusTierA:
	db GOLDUCK      ;  55  BST 500  stage 1
	db TENTACRUEL   ;  73  BST 515  stage 1
	db RAPIDASH     ;  78  BST 500  stage 1
	db SLOWBRO      ;  80  BST 490  stage 1
	db DODRIO       ;  85  BST 460  stage 1
	db MUK          ;  89  BST 500  stage 1
	db HYPNO        ;  97  BST 483  stage 1
	db KINGLER      ;  99  BST 475  stage 1
	db WEEZING      ; 110  BST 490  stage 1
	db RHYDON       ; 112  BST 485  stage 1
	db CHANSEY      ; 113  BST 450  stage 0
	db KANGASKHAN   ; 115  BST 490  stage 0
	db MR__MIME     ; 122  BST 460  stage 0
	db SCYTHER      ; 123  BST 500  stage 0
	db ELECTABUZZ   ; 125  BST 490  stage 1
	db MAGMAR       ; 126  BST 495  stage 1
	db PINSIR       ; 127  BST 500  stage 0
	db TAUROS       ; 128  BST 490  stage 0
	db GYARADOS     ; 130  BST 540  stage 1
	db LANTURN      ; 171  BST 460  stage 1
	db HERACROSS    ; 214  BST 500  stage 0
	db URSARING     ; 217  BST 500  stage 1
	db MANTINE      ; 226  BST 465  stage 0
	db SKARMORY     ; 227  BST 465  stage 0
	db DONPHAN      ; 232  BST 500  stage 1
	db STANTLER     ; 234  BST 465  stage 0
	db MILTANK      ; 241  BST 490  stage 0
	db -1 ; end
