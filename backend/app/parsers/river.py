import logging

from app.models.enums import RiverActionSequence, ShowdownType

from .common import RIVER_RE, ACTION_RE, HERO_SHOWDOWN_RE, TOTAL_POT_RE

logger = logging.getLogger(__name__)


def parse_river_actions(lines: list[str]) -> tuple[bool, bool, bool, bool, bool, bool]:
	in_river = False
	hero_bet_river = False
	villain_fold_to_hero_bet = False
	villain_raise_to_hero_bet = False
	villain_bet_river = False
	hero_fold_to_villain_bet = False
	hero_raise_to_villain_bet = False

	for line in lines:
		if RIVER_RE.search(line):
			in_river = True
			continue

		if not in_river:
			continue

		if any(m in line for m in ["*** SHOWDOWN ***", "*** SUMMARY ***"]):
			break

		action = ACTION_RE.search(line)
		if not action:
			continue

		actor = action.group(1)
		act = action.group(2).lower()

		if hero_bet_river and actor != "Hero":
			if act == "folds":
				villain_fold_to_hero_bet = True
			elif act == "raises":
				villain_raise_to_hero_bet = True
			return hero_bet_river, villain_fold_to_hero_bet, villain_raise_to_hero_bet, villain_bet_river, hero_fold_to_villain_bet, hero_raise_to_villain_bet

		if villain_bet_river and actor == "Hero":
			if act == "folds":
				hero_fold_to_villain_bet = True
			elif act == "raises":
				hero_raise_to_villain_bet = True
			return hero_bet_river, villain_fold_to_hero_bet, villain_raise_to_hero_bet, villain_bet_river, hero_fold_to_villain_bet, hero_raise_to_villain_bet

		if not hero_bet_river and not villain_bet_river:
			if actor == "Hero" and act == "bets":
				hero_bet_river = True
			elif actor != "Hero" and act == "bets":
				villain_bet_river = True

	return hero_bet_river, villain_fold_to_hero_bet, villain_raise_to_hero_bet, villain_bet_river, hero_fold_to_villain_bet, hero_raise_to_villain_bet


def parse_river_showdown_type(lines: list[str]) -> ShowdownType | None:
	in_river = False
	has_bet = False
	has_raise = False

	for line in lines:
		if RIVER_RE.search(line):
			in_river = True
			continue

		if not in_river:
			continue

		if any(m in line for m in ["*** SHOWDOWN ***", "*** SUMMARY ***"]):
			break

		action = ACTION_RE.search(line)
		if not action:
			continue

		act = action.group(2).lower()
		if act == "bets":
			has_bet = True
		elif act == "raises":
			has_raise = True

	if has_raise:
		return ShowdownType.RAISE_OCCURRED
	if has_bet:
		return ShowdownType.BET_CALL
	return ShowdownType.CHECK_CHECK


def parse_river_action_sequence(lines: list[str]) -> RiverActionSequence | None:
	in_river = False
	sequence = ""

	for line in lines:
		if RIVER_RE.search(line):
			in_river = True
			continue

		if not in_river:
			continue

		if any(m in line for m in ["*** SHOWDOWN ***", "*** SUMMARY ***"]):
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
		elif act == "folds":
			sequence += "F"

	if sequence == "XX":
		return RiverActionSequence.XX
	elif sequence in ("XBC", "XBF"):
		return RiverActionSequence.XBC
	elif sequence in ("XBRC", "XBRF"):
		return RiverActionSequence.XBRC
	elif sequence in ("BC", "BF"):
		return RiverActionSequence.BC

	return None


def parse_showdown_result(lines: list[str]) -> tuple[bool, bool, float]:
	went_to_showdown = False
	hero_won = False
	pot_size_bb = 0.0

	for line in lines:
		m = HERO_SHOWDOWN_RE.search(line)
		if m:
			went_to_showdown = True
			hero_won = m.group(1) == "won"

	for line in lines:
		m = TOTAL_POT_RE.search(line)
		if m:
			pot_size_bb = float(m.group(1)) / 0.02
			break

	return went_to_showdown, hero_won, pot_size_bb
