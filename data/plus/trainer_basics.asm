; Trainer roster randomizer - basic-stage draw pool
;
; Every TRAINERTYPE_NORMAL mon is replaced by a species drawn from here and
; then evolved forward with a level discount, so only stage-0 species are
; listed: the evolved forms reach the field through their own lines.
;
; POOL: the 117 species that are never the target of an evolution, minus the
; 11 legendaries and Unown, minus the 11 exclusions below. 106 remain.
;
; Banded by base stat total, computed from data/pokemon/base_stats:
;   PlusTrainerBasicsLate   BST 430 and up   22 species   levels 30+
;   PlusTrainerBasicsMid    BST 300 to 429   56 species   levels 15-29
;   PlusTrainerBasicsEarly  BST below 300    28 species   any level
;
; The bands fall through, so one label selects a subset: Late runs into Mid
; runs into Early. A trainer under level 15 reads PlusTrainerBasicsEarly and
; sees 28 species, one from 15 to 29 reads PlusTrainerBasicsMid and sees 84,
; one at 30 or above reads PlusTrainerBasicsLate and sees all 106.
;
; EXCLUDED (11):
;   BULBASAUR CHARMANDER SQUIRTLE CHIKORITA CYNDAQUIL TOTODILE
;                 starters, and with them their whole lines; the starter is
;                 the one species the randomizer treats as special
;   MAGIKARP      Splash only until Tackle at 15, and nothing after
;   DITTO         Transform is its entire movepool
;   WOBBUFFET     no damaging move at any level
;   SMEARGLE      a generated moveset is four copies of Sketch
;   SHUCKLE       505 BST is all defence behind 10 Atk and 10 SpA; it cannot
;                 win a battle, only prolong one
;
; HAND-BANDED (4), where the base stat total misreads how the species plays:
;   ABRA      Early -> Late  Teleport is its only level-up move, so a bare
;                            Abra cannot attack. From level 30 the discount
;                            always clears Kadabra's 16. Alakazam needs
;                            level 40, above anything a normal trainer
;                            fields today.
;   TOGEPI    Early -> Late  no damaging level-up move before Double-Edge at
;                            38. From level 30 it is always Togetic.
;   HOPPIP    Early -> Mid   Splash and Synthesis until Tackle at 13
;   IGGLYBUFF Early -> Mid   Sing and Charm until Pound at 14

PlusTrainerBasicsLate:
	db ABRA         ;  63  BST 310, hand-banded
	db CHANSEY      ; 113  BST 450
	db TANGELA      ; 114  BST 435
	db KANGASKHAN   ; 115  BST 490
	db MR__MIME     ; 122  BST 460
	db SCYTHER      ; 123  BST 500
	db PINSIR       ; 127  BST 500
	db TAUROS       ; 128  BST 490
	db LAPRAS       ; 131  BST 535
	db AERODACTYL   ; 142  BST 515
	db SNORLAX      ; 143  BST 540
	db TOGEPI       ; 175  BST 245, hand-banded
	db MISDREAVUS   ; 200  BST 435
	db GIRAFARIG    ; 203  BST 455
	db GLIGAR       ; 207  BST 430
	db QWILFISH     ; 211  BST 430
	db HERACROSS    ; 214  BST 500
	db SNEASEL      ; 215  BST 430
	db MANTINE      ; 226  BST 465
	db SKARMORY     ; 227  BST 465
	db STANTLER     ; 234  BST 465
	db MILTANK      ; 241  BST 490
	; fallthrough
PlusTrainerBasicsMid:
	db SANDSHREW    ;  27  BST 300
	db ODDISH       ;  43  BST 320
	db VENONAT      ;  48  BST 305
	db PSYDUCK      ;  54  BST 320
	db MANKEY       ;  56  BST 305
	db GROWLITHE    ;  58  BST 350
	db POLIWAG      ;  60  BST 300
	db MACHOP       ;  66  BST 305
	db BELLSPROUT   ;  69  BST 300
	db TENTACOOL    ;  72  BST 335
	db GEODUDE      ;  74  BST 300
	db PONYTA       ;  77  BST 410
	db SLOWPOKE     ;  79  BST 315
	db MAGNEMITE    ;  81  BST 325
	db FARFETCH_D   ;  83  BST 352
	db DODUO        ;  84  BST 310
	db SEEL         ;  86  BST 325
	db GRIMER       ;  88  BST 325
	db SHELLDER     ;  90  BST 305
	db GASTLY       ;  92  BST 310
	db ONIX         ;  95  BST 385
	db DROWZEE      ;  96  BST 328
	db KRABBY       ;  98  BST 325
	db VOLTORB      ; 100  BST 330
	db EXEGGCUTE    ; 102  BST 325
	db CUBONE       ; 104  BST 320
	db LICKITUNG    ; 108  BST 385
	db KOFFING      ; 109  BST 340
	db RHYHORN      ; 111  BST 345
	db GOLDEEN      ; 118  BST 320
	db STARYU       ; 120  BST 340
	db EEVEE        ; 133  BST 325
	db PORYGON      ; 137  BST 395
	db OMANYTE      ; 138  BST 355
	db KABUTO       ; 140  BST 355
	db DRATINI      ; 147  BST 300
	db CHINCHOU     ; 170  BST 330
	db IGGLYBUFF    ; 174  BST 210, hand-banded
	db NATU         ; 177  BST 320
	db SUDOWOODO    ; 185  BST 410
	db HOPPIP       ; 187  BST 250, hand-banded
	db AIPOM        ; 190  BST 360
	db YANMA        ; 193  BST 390
	db MURKROW      ; 198  BST 405
	db DUNSPARCE    ; 206  BST 415
	db SNUBBULL     ; 209  BST 300
	db TEDDIURSA    ; 216  BST 330
	db CORSOLA      ; 222  BST 380
	db REMORAID     ; 223  BST 300
	db DELIBIRD     ; 225  BST 330
	db HOUNDOUR     ; 228  BST 330
	db PHANPY       ; 231  BST 330
	db SMOOCHUM     ; 238  BST 305
	db ELEKID       ; 239  BST 360
	db MAGBY        ; 240  BST 365
	db LARVITAR     ; 246  BST 300
	; fallthrough
PlusTrainerBasicsEarly:
	db CATERPIE     ;  10  BST 195
	db WEEDLE       ;  13  BST 195
	db PIDGEY       ;  16  BST 251
	db RATTATA      ;  19  BST 253
	db SPEAROW      ;  21  BST 262
	db EKANS        ;  23  BST 288
	db NIDORAN_F    ;  29  BST 275
	db NIDORAN_M    ;  32  BST 273
	db VULPIX       ;  37  BST 299
	db ZUBAT        ;  41  BST 245
	db PARAS        ;  46  BST 285
	db DIGLETT      ;  50  BST 265
	db MEOWTH       ;  52  BST 290
	db HORSEA       ; 116  BST 295
	db SENTRET      ; 161  BST 215
	db HOOTHOOT     ; 163  BST 262
	db LEDYBA       ; 165  BST 265
	db SPINARAK     ; 167  BST 250
	db PICHU        ; 172  BST 205
	db CLEFFA       ; 173  BST 218
	db MAREEP       ; 179  BST 280
	db MARILL       ; 183  BST 250
	db SUNKERN      ; 191  BST 180
	db WOOPER       ; 194  BST 210
	db PINECO       ; 204  BST 290
	db SLUGMA       ; 218  BST 250
	db SWINUB       ; 220  BST 250
	db TYROGUE      ; 236  BST 210
	db -1 ; end
