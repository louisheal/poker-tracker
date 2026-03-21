import logging

from app.models.events import FlopAction
from app.models.enums import FlopActionSequence

from .common import FLOP_RE, ACTION_RE, BET_AMOUNT_RE, CALL_AMOUNT_RE, RAISE_INC_RE

logger = logging.getLogger(__name__)


def parse_flop_cbet(lines: list[str], hero_is_pfr: bool) -> tuple[bool, bool, bool, bool, bool, bool, float | None, float | None]:

	in_flop = False
	cbet = False
	fold_to_cbet = False
	raise_to_cbet = False
	donk_bet = False
	fold_to_donk_bet = False
	raise_to_donk_bet = False
	cbet_amount: float | None = None
	donk_bet_amount: float | None = None

	for line in lines:

		if FLOP_RE.search(line):
			in_flop = True
			continue

		if not in_flop:
			continue

		if any(m in line for m in ["*** TURN ***", "*** RIVER ***", "*** SHOWDOWN ***", "*** SUMMARY ***"]):
			break

		action = ACTION_RE.search(line)
		if not action:
			continue

		actor = action.group(1)
		act = action.group(2).lower()
		pfr_actor = actor == "Hero" if hero_is_pfr else actor != "Hero"

		if cbet and not pfr_actor:
			if act == "folds":
				fold_to_cbet = True
			elif act == "raises":
				raise_to_cbet = True
			return cbet, fold_to_cbet, raise_to_cbet, donk_bet, fold_to_donk_bet, raise_to_donk_bet, cbet_amount, donk_bet_amount
		
		if donk_bet and pfr_actor:
			if act == "folds":
				fold_to_donk_bet = True
			elif act == "raises":
				raise_to_donk_bet = True
			return cbet, fold_to_cbet, raise_to_cbet, donk_bet, fold_to_donk_bet, raise_to_donk_bet, cbet_amount, donk_bet_amount
		
		if cbet or donk_bet:
			continue

		if pfr_actor and act == "bets":
			cbet = True
			m = BET_AMOUNT_RE.search(line)
			if m:
				cbet_amount = float(m.group(1))
			continue

		if not pfr_actor and act == "bets":
			donk_bet = True
			m = BET_AMOUNT_RE.search(line)
			if m:
				donk_bet_amount = float(m.group(1))
			continue
	
	return cbet, fold_to_cbet, raise_to_cbet, donk_bet, fold_to_donk_bet, raise_to_donk_bet, cbet_amount, donk_bet_amount


def parse_flop_actions_detailed(lines: list[str], hero_ip: bool, pot_at_flop_bb: float) -> list[FlopAction]:
	"""Parse the full ordered sequence of flop actions with sizes as pot %."""
	actions: list[FlopAction] = []
	in_flop = False
	# Track running pot in dollars for sizing calculations
	pot = pot_at_flop_bb * 0.02

	for line in lines:
		if FLOP_RE.search(line):
			in_flop = True
			continue
		if not in_flop:
			continue
		if any(m in line for m in ["*** TURN ***", "*** RIVER ***", "*** SHOWDOWN ***", "*** SUMMARY ***"]):
			break

		action_m = ACTION_RE.search(line)
		if not action_m:
			continue

		actor_name = action_m.group(1)
		act = action_m.group(2).lower()
		actor = "hero" if actor_name == "Hero" else "villain"

		if act == "checks":
			actions.append(FlopAction(actor=actor, action="X"))
		elif act == "folds":
			actions.append(FlopAction(actor=actor, action="F"))
			break  # Hand over on this street
		elif act == "bets":
			m = BET_AMOUNT_RE.search(line)
			size_pct = None
			if m and pot > 0:
				amt = float(m.group(1))
				size_pct = round((amt / pot) * 100, 1)
				pot += amt
			actions.append(FlopAction(actor=actor, action="B", size_pct=size_pct))
		elif act == "calls":
			m = CALL_AMOUNT_RE.search(line)
			if m:
				pot += float(m.group(1))
			actions.append(FlopAction(actor=actor, action="C"))
		elif act == "raises":
			m = RAISE_INC_RE.search(line)
			size_pct = None
			if m and pot > 0:
				inc = float(m.group(1))
				total = float(m.group(2))
				# Raise size relative to pot before the raise
				size_pct = round((total / pot) * 100, 1)
				pot += inc
			actions.append(FlopAction(actor=actor, action="R", size_pct=size_pct))

	return actions


def parse_flop_action_sequence(lines: list[str], hero_is_pfr: bool) -> FlopActionSequence | None:
	in_flop = False
	sequence = ""
	
	for line in lines:
		if FLOP_RE.search(line):
			in_flop = True
			continue
		
		if not in_flop:
			continue
		
		if any(m in line for m in ["*** TURN ***", "*** RIVER ***", "*** SHOWDOWN ***", "*** SUMMARY ***"]):
			break
		
		action = ACTION_RE.search(line)
		if not action:
			continue
		
		actor = action.group(1)
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
		return FlopActionSequence.XX
	elif sequence == "XBC":
		return FlopActionSequence.XBC
	elif sequence == "XBRC":
		return FlopActionSequence.XBRC
	elif sequence == "BC":
		return FlopActionSequence.BC
	
	return None


def _parse_fold_to_raise(lines: list[str], hero_is_pfr: bool, is_cbet: bool) -> bool:
	"""Check if the initial bettor folded after being raised on flop."""
	in_flop = False
	bet_seen = False
	raise_seen = False

	for line in lines:
		if FLOP_RE.search(line):
			in_flop = True
			continue
		if not in_flop:
			continue
		if any(m in line for m in ["*** TURN ***", "*** RIVER ***", "*** SHOWDOWN ***", "*** SUMMARY ***"]):
			break

		action = ACTION_RE.search(line)
		if not action:
			continue

		actor = action.group(1)
		act = action.group(2).lower()
		pfr_actor = actor == "Hero" if hero_is_pfr else actor != "Hero"

		if is_cbet:
			# Track: PFR bets (cbet), non-PFR raises, PFR folds
			if not bet_seen and pfr_actor and act == "bets":
				bet_seen = True
			elif bet_seen and not raise_seen and not pfr_actor and act == "raises":
				raise_seen = True
			elif raise_seen and pfr_actor and act == "folds":
				return True
		else:
			# Track: non-PFR bets (donk), PFR raises, non-PFR folds
			if not bet_seen and not pfr_actor and act == "bets":
				bet_seen = True
			elif bet_seen and not raise_seen and pfr_actor and act == "raises":
				raise_seen = True
			elif raise_seen and not pfr_actor and act == "folds":
				return True

	return False
