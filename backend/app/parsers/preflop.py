import logging

from playing_cards_lib.poker import PokerPosition, PotType

from .common import (
	FLOP_RE, ACTION_RE, BLIND_RE, RAISE_TO_AMOUNT_RE,
	CALL_AMOUNT_RE, BET_AMOUNT_RE, UNCALLED_RE,
	HERO_COLLECTED_RE, HERO_WON_RE,
)

logger = logging.getLogger(__name__)


def parse_hero_sees_flop(lines: list[str]) -> bool:
	for line in lines:
		if FLOP_RE.search(line):
			return True
		action = ACTION_RE.search(line)
		if action and action.group(1) == "Hero" and action.group(2).lower() == "folds":
			return False
	return False


def parse_preflop_pot_type(lines: list[str]) -> PotType:
	raise_count = 0
	for line in lines:
		if "*** FLOP ***" in line:
			break
		action = ACTION_RE.search(line)
		if action and action.group(2).lower() == "raises":
			raise_count += 1
	if raise_count >= 3:
		return PotType.FOUR_BET
	elif raise_count >= 2:
		return PotType.THREE_BET
	return PotType.SRP


def parse_hero_in_position(lines: list[str]) -> bool:
	in_flop = False
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
		return action.group(1) != "Hero"
	return False


def parse_pot_at_flop(lines: list[str]) -> float | None:
	"""Compute pot at flop by tracking per-player preflop contributions. Returns pot in BB."""
	contributions: dict[str, float] = {}
	in_preflop = False

	for line in lines:
		if "*** HOLE CARDS ***" in line:
			in_preflop = True
			continue
		if not in_preflop:
			continue
		if "*** FLOP ***" in line:
			break

		m = BLIND_RE.search(line)
		if m:
			colon_idx = line.find(": posts")
			if colon_idx > 0:
				player = line[:colon_idx].strip()
				contributions[player] = contributions.get(player, 0) + float(m.group(1))
			continue

		m = RAISE_TO_AMOUNT_RE.search(line)
		if m:
			colon_idx = line.find(": raises")
			if colon_idx > 0:
				player = line[:colon_idx].strip()
				# "raises $X to $Y" — Y is the player's total contribution this round
				contributions[player] = float(m.group(1))
			continue

		m = CALL_AMOUNT_RE.search(line)
		if m:
			colon_idx = line.find(": calls")
			if colon_idx > 0:
				player = line[:colon_idx].strip()
				contributions[player] = contributions.get(player, 0) + float(m.group(1))
			continue

		m = BET_AMOUNT_RE.search(line)
		if m:
			colon_idx = line.find(": bets")
			if colon_idx > 0:
				player = line[:colon_idx].strip()
				contributions[player] = contributions.get(player, 0) + float(m.group(1))
			continue

	if not contributions:
		return None

	pot_dollars = sum(contributions.values())
	if pot_dollars <= 0:
		return None
	return pot_dollars / 0.02


def parse_hero_pnl(lines: list[str]) -> tuple[float, float] | None:
	"""Compute hero's net profit/loss in BB for this hand.
	
	Returns (hero_pnl_bb, hero_preflop_invested_bb) or None if hero had no action.
	
	hero_pnl_bb = whole hand P&L in BB
	hero_preflop_invested_bb = hero's preflop contribution in BB
	
	Flop-onwards EV = hero_pnl_bb + hero_preflop_invested_bb
	"""
	hero_invested = 0.0
	hero_collected = 0.0
	hero_round_invested = 0.0
	hero_preflop_invested = 0.0
	past_preflop = False

	for line in lines:
		# Reset per-round tracking at street boundaries
		if any(marker in line for marker in ["*** FLOP ***", "*** TURN ***", "*** RIVER ***"]):
			if not past_preflop:
				hero_preflop_invested = hero_invested
				past_preflop = True
			hero_round_invested = 0.0

		# Track hero's contributions
		if "Hero:" in line or ("Hero" in line and "posts" in line):
			if "posts" in line and "blind" in line:
				m = BLIND_RE.search(line)
				if m:
					amt = float(m.group(1))
					hero_invested += amt
					hero_round_invested += amt
			elif ": calls" in line:
				m = CALL_AMOUNT_RE.search(line)
				if m:
					amt = float(m.group(1))
					hero_invested += amt
					hero_round_invested += amt
			elif ": bets" in line:
				m = BET_AMOUNT_RE.search(line)
				if m:
					amt = float(m.group(1))
					hero_invested += amt
					hero_round_invested += amt
			elif ": raises" in line:
				m = RAISE_TO_AMOUNT_RE.search(line)
				if m:
					total_round = float(m.group(1))
					new_money = total_round - hero_round_invested
					hero_invested += new_money
					hero_round_invested = total_round

		# Track uncalled bets returned to hero
		if "Uncalled bet" in line and "returned to Hero" in line:
			m = UNCALLED_RE.search(line)
			if m:
				hero_invested -= float(m.group(1))

		# Track hero's winnings
		m = HERO_COLLECTED_RE.search(line)
		if m:
			hero_collected += float(m.group(1))
			continue
		m = HERO_WON_RE.search(line)
		if m:
			hero_collected = float(m.group(1))

	if hero_invested == 0.0 and hero_collected == 0.0:
		return None

	# If hand never reached flop, all investment is preflop
	if not past_preflop:
		hero_preflop_invested = hero_invested

	pnl_bb = (hero_collected - hero_invested) / 0.02
	preflop_bb = hero_preflop_invested / 0.02
	return (pnl_bb, preflop_bb)


def parse_hero_preflop_raiser(lines: list[str]) -> bool:
	last_raiser = None

	for line in lines:
		if "*** FLOP ***" in line:
			break

		action = ACTION_RE.search(line)
		if not action:
			continue

		act = action.group(2)
		if act == "raises":
			last_raiser = action.group(1)
	
	return last_raiser == "Hero"
		

def parse_hero_position(lines: list[str]):
	p = 0
	for line in lines:
		action = ACTION_RE.search(line)
		if not action:
			continue
		if action.group(1) == "Hero":
			return PokerPosition(p)
		p += 1
	return PokerPosition.BB
