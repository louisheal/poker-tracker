import logging

from app.models.enums import TurnActionSequence

from .common import TURN_RE, ACTION_RE

logger = logging.getLogger(__name__)


def parse_turn_actions(lines: list[str]) -> tuple[bool, bool, bool, bool, bool, bool]:
	in_turn = False
	hero_bet_turn = False
	villain_fold_to_hero_bet = False
	villain_raise_to_hero_bet = False
	villain_bet_turn = False
	hero_fold_to_villain_bet = False
	hero_raise_to_villain_bet = False
	
	for line in lines:
		if TURN_RE.search(line):
			in_turn = True
			continue
		
		if not in_turn:
			continue
		
		if any(m in line for m in ["*** RIVER ***", "*** SHOWDOWN ***", "*** SUMMARY ***"]):
			break
		
		action = ACTION_RE.search(line)
		if not action:
			continue
		
		actor = action.group(1)
		act = action.group(2).lower()
		
		if hero_bet_turn and actor != "Hero":
			if act == "folds":
				villain_fold_to_hero_bet = True
			elif act == "raises":
				villain_raise_to_hero_bet = True
			# Stop after first response
			return hero_bet_turn, villain_fold_to_hero_bet, villain_raise_to_hero_bet, villain_bet_turn, hero_fold_to_villain_bet, hero_raise_to_villain_bet
		
		if villain_bet_turn and actor == "Hero":
			if act == "folds":
				hero_fold_to_villain_bet = True
			elif act == "raises":
				hero_raise_to_villain_bet = True
			# Stop after first response
			return hero_bet_turn, villain_fold_to_hero_bet, villain_raise_to_hero_bet, villain_bet_turn, hero_fold_to_villain_bet, hero_raise_to_villain_bet
		
		if not hero_bet_turn and not villain_bet_turn:
			if actor == "Hero" and act == "bets":
				hero_bet_turn = True
			elif actor != "Hero" and act == "bets":
				villain_bet_turn = True
	
	return hero_bet_turn, villain_fold_to_hero_bet, villain_raise_to_hero_bet, villain_bet_turn, hero_fold_to_villain_bet, hero_raise_to_villain_bet


def parse_turn_action_sequence(lines: list[str]) -> TurnActionSequence | None:
	in_turn = False
	sequence = ""

	for line in lines:
		if TURN_RE.search(line):
			in_turn = True
			continue

		if not in_turn:
			continue

		if any(m in line for m in ["*** RIVER ***", "*** SHOWDOWN ***", "*** SUMMARY ***"]):
			break

		action = ACTION_RE.search(line)
		if not action:
			continue

		act = action.group(2).lower()

		if act == "checks":
			sequence += "X"
		elif act == "bets":
			sequence += "B"
		elif act == "raises":
			sequence += "R"
		elif act == "calls":
			sequence += "C"

	if sequence == "XX":
		return TurnActionSequence.XX
	elif sequence == "XBC":
		return TurnActionSequence.XBC
	elif sequence == "XBRC":
		return TurnActionSequence.XBRC
	elif sequence == "BC":
		return TurnActionSequence.BC

	return None
