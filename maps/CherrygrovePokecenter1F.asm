	object_const_def
	const CHERRYGROVEPOKECENTER1F_NURSE
	const CHERRYGROVEPOKECENTER1F_FISHER
	const CHERRYGROVEPOKECENTER1F_GENTLEMAN
	const CHERRYGROVEPOKECENTER1F_TEACHER
	const CHERRYGROVEPOKECENTER1F_SCIENTIST ; plus: trainer roster randomizer

CherrygrovePokecenter1F_MapScripts:
	def_scene_scripts

	def_callbacks

CherrygrovePokecenter1FNurseScript:
	jumpstd PokecenterNurseScript

CherrygrovePokecenter1FFisherScript:
	jumptextfaceplayer CherrygrovePokecenter1FFisherText

CherrygrovePokecenter1FGentlemanScript:
	jumptextfaceplayer CherrygrovePokecenter1FGentlemanText

CherrygrovePokecenter1FTeacherScript:
	faceplayer
	opentext
	checkevent EVENT_GAVE_MYSTERY_EGG_TO_ELM
	iftrue .CommCenterOpen
	writetext CherrygrovePokecenter1FTeacherText
	waitbutton
	closetext
	end

.CommCenterOpen:
	writetext CherrygrovePokecenter1FTeacherText_CommCenterOpen
	waitbutton
	closetext
	end

; plus: trainer roster randomizer toggle
CherrygrovePokecenter1FScientistScript:
	faceplayer
	opentext
	callasm PlusCheckTrainersEnabled
	ifequal TRUE, .TurnItOff
	writetext CherrygrovePokecenter1FScientistText_Offer
	yesorno
	iffalse .Declined
	callasm PlusToggleTrainers
	writetext CherrygrovePokecenter1FScientistText_TurnedOn
	waitbutton
	closetext
	end

.TurnItOff:
	writetext CherrygrovePokecenter1FScientistText_Restore
	yesorno
	iffalse .Declined
	callasm PlusToggleTrainers
	writetext CherrygrovePokecenter1FScientistText_TurnedOff
	waitbutton
	closetext
	end

.Declined:
	writetext CherrygrovePokecenter1FScientistText_Declined
	waitbutton
	closetext
	end

CherrygrovePokecenter1FFisherText:
	text "It's great. I can"
	line "store any number"

	para "of #MON, and"
	line "it's all free."
	done

CherrygrovePokecenter1FGentlemanText:
	text "That PC is free"
	line "for any trainer"
	cont "to use."
	done

CherrygrovePokecenter1FTeacherText:
	text "The COMMUNICATION"
	line "CENTER upstairs"
	cont "was just built."

	para "But they're still"
	line "finishing it up."
	done

CherrygrovePokecenter1FTeacherText_CommCenterOpen:
	text "The COMMUNICATION"
	line "CENTER upstairs"
	cont "was just built."

	para "I traded #MON"
	line "there already!"
	done

; plus: trainer roster randomizer toggle
CherrygrovePokecenter1FScientistText_Offer:
	text "I can shuffle the"
	line "#MON that"
	cont "trainers use."

	para "GYM LEADERS and"
	line "the like keep"
	cont "their own teams."

	para "Shall I mix up"
	line "the rest?"
	done

CherrygrovePokecenter1FScientistText_TurnedOn:
	text "It's done!"

	para "Every trainer out"
	line "there is a bit of"
	cont "a surprise now."
	done

CherrygrovePokecenter1FScientistText_Restore:
	text "Trainers are"
	line "battling with"
	cont "shuffled teams."

	para "Shall I put them"
	line "back to normal?"
	done

CherrygrovePokecenter1FScientistText_TurnedOff:
	text "All set!"

	para "Everyone fights"
	line "with their own"
	cont "#MON again."
	done

CherrygrovePokecenter1FScientistText_Declined:
	text "Fine by me."

	para "Drop by if you"
	line "change your mind."
	done

CherrygrovePokecenter1F_MapEvents:
	db 0, 0 ; filler

	def_warp_events
	warp_event  3,  7, CHERRYGROVE_CITY, 2
	warp_event  4,  7, CHERRYGROVE_CITY, 2
	warp_event  0,  7, POKECENTER_2F, 1

	def_coord_events

	def_bg_events

	def_object_events
	object_event  3,  1, SPRITE_NURSE, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, CherrygrovePokecenter1FNurseScript, -1
	object_event  2,  3, SPRITE_FISHER, SPRITEMOVEDATA_STANDING_UP, 0, 0, -1, -1, PAL_NPC_RED, OBJECTTYPE_SCRIPT, 0, CherrygrovePokecenter1FFisherScript, -1
	object_event  8,  6, SPRITE_GENTLEMAN, SPRITEMOVEDATA_STANDING_UP, 0, 0, -1, -1, 0, OBJECTTYPE_SCRIPT, 0, CherrygrovePokecenter1FGentlemanScript, -1
	object_event  1,  6, SPRITE_TEACHER, SPRITEMOVEDATA_STANDING_RIGHT, 0, 0, -1, -1, PAL_NPC_GREEN, OBJECTTYPE_SCRIPT, 0, CherrygrovePokecenter1FTeacherScript, -1
	object_event  7,  3, SPRITE_SCIENTIST, SPRITEMOVEDATA_STANDING_DOWN, 0, 0, -1, -1, PAL_NPC_BLUE, OBJECTTYPE_SCRIPT, 0, CherrygrovePokecenter1FScientistScript, -1 ; plus: trainer roster randomizer
