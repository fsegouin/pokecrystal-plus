TalkToTrainerScript::
	faceplayer
	trainerflagaction CHECK_FLAG
	iftrue OfferRematchScript ; plus: rematches
	loadtemptrainer
	encountermusic
	sjump StartBattleWithMapTrainerScript

SeenByTrainerScript::
	loadtemptrainer
	encountermusic
	showemote EMOTE_SHOCK, LAST_TALKED, 30
	callasm TrainerWalkToPlayer
	applymovementlasttalked wMovementBuffer
	writeobjectxy LAST_TALKED
	faceobject PLAYER, LAST_TALKED
	sjump StartBattleWithMapTrainerScript

StartBattleWithMapTrainerScript:
	opentext
	trainertext TRAINERTEXT_SEEN
	waitbutton
	closetext
	loadtemptrainer
	startbattle
	reloadmapafterbattle
	trainerflagaction SET_FLAG
	loadmem wRunningTrainerBattleScript, -1

AlreadyBeatenTrainerScript:
	scripttalkafter

; plus: every beaten map trainer offers a rematch when the player talks to it.
; Only TalkToTrainerScript branches here. The fall-through above still runs the
; plain after-battle script, so the offer never reappears on the turn a battle
; ends and no debounce is needed. Declining falls back to the after-battle
; script, which is what vanilla would have shown.
OfferRematchScript:
	opentext
	writetext RematchOfferText
	yesorno
	iffalse .decline
	closetext
	loadtemptrainer
	encountermusic
	sjump StartBattleWithMapTrainerScript

.decline
	closetext
	sjump AlreadyBeatenTrainerScript

RematchOfferText::
; Shared with the gym leader rematch branches, which farwritetext it.
	text "Want to take me"
	line "on again?"
	done
