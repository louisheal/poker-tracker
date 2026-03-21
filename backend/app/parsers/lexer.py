"""Single-pass lexer: converts hand history lines into a HandAST."""

import re
import logging
from datetime import datetime

from .common import (
	START_RE, DEALT_HERO_RE, ACTION_RE,
	BET_AMOUNT_RE, CALL_AMOUNT_RE, RAISE_INC_RE,
	UNCALLED_RE, HERO_COLLECTED_RE, HERO_WON_RE,
	HERO_SHOWDOWN_RE, TOTAL_POT_RE,
	FLOP_RE, TURN_RE, RIVER_RE, SEAT_RE,
	to_card, to_hole_cards,
)
from .ast import HandAST, Action, ActionType, BlindPost, Street

logger = logging.getLogger(__name__)

BUTTON_RE = re.compile(r"Seat #(\d+) is the button")
SEAT_STACK_RE = re.compile(r"^Seat\s+(\d+):\s+(\S+)\s+\(\$(\d+\.?\d*)\s+in chips\)")
BLIND_POST_RE = re.compile(r"^(.+?):\s+posts\s+(small|big)\s+blind\s+\$(\d+\.?\d*)")
UNCALLED_FULL_RE = re.compile(r"Uncalled bet \(\$(\d+\.?\d*)\) returned to (.+)")

_STREET_END = frozenset(["*** TURN ***", "*** RIVER ***", "*** SHOWDOWN ***", "*** SUMMARY ***"])


class _State:
	SEATS = 0
	HOLE_CARDS = 1
	PREFLOP = 2
	FLOP = 3
	TURN = 4
	RIVER = 5
	SHOWDOWN = 6
	SUMMARY = 7


def _parse_action(line: str, action_m: re.Match) -> Action:
	"""Build an Action from an ACTION_RE match, extracting amounts from the line."""
	player = action_m.group(1)
	act = action_m.group(2).lower()
	is_hero = player == "Hero"

	if act == "folds":
		return Action(player=player, type=ActionType.FOLD, is_hero=is_hero)
	elif act == "checks":
		return Action(player=player, type=ActionType.CHECK, is_hero=is_hero)
	elif act == "calls":
		amt_m = CALL_AMOUNT_RE.search(line)
		amount = float(amt_m.group(1)) if amt_m else None
		return Action(player=player, type=ActionType.CALL, amount=amount, is_hero=is_hero)
	elif act == "bets":
		amt_m = BET_AMOUNT_RE.search(line)
		amount = float(amt_m.group(1)) if amt_m else None
		return Action(player=player, type=ActionType.BET, amount=amount, is_hero=is_hero)
	else:  # raises
		raise_m = RAISE_INC_RE.search(line)
		if raise_m:
			return Action(
				player=player, type=ActionType.RAISE,
				amount=float(raise_m.group(1)),
				raise_to=float(raise_m.group(2)),
				is_hero=is_hero,
			)
		return Action(player=player, type=ActionType.RAISE, is_hero=is_hero)


def lex_hand(lines: list[str]) -> HandAST | None:
	"""Single-pass lexer: converts hand history lines into a HandAST."""
	if not lines:
		return None

	# Header (line 0)
	m = START_RE.search(lines[0])
	if not m:
		return None
	hand_id_m = re.search(r"Poker Hand #([^:]+)", lines[0])
	hand_id = hand_id_m.group(1) if hand_id_m else ""
	played_on = datetime.strptime(m.group(1), "%Y/%m/%d").date()

	# Table info (line 1)
	button_seat = 1
	if len(lines) > 1:
		btn_m = BUTTON_RE.search(lines[1])
		if btn_m:
			button_seat = int(btn_m.group(1))

	# AST accumulators
	players: list[tuple[str, int, float]] = []
	hero_hole_cards = None
	blinds: list[BlindPost] = []
	preflop: list[Action] = []
	flop: Street | None = None
	turn: Street | None = None
	river: Street | None = None
	hero_collected = 0.0
	total_pot = 0.0
	uncalled_amount = 0.0
	uncalled_to: str | None = None
	hero_showed_won: bool | None = None

	state = _State.SEATS
	current_actions = preflop

	for line in lines[2:]:
		# ---- Section markers ----
		if line.startswith("*** "):
			if "HOLE CARDS" in line:
				state = _State.HOLE_CARDS
				continue

			flop_m = FLOP_RE.search(line)
			if flop_m:
				cards = [to_card(flop_m.group(i)) for i in (1, 2, 3)]
				flop = Street(cards=cards)
				current_actions = flop.actions
				state = _State.FLOP
				continue

			turn_m = TURN_RE.search(line)
			if turn_m:
				turn = Street(cards=[to_card(turn_m.group(4))])
				current_actions = turn.actions
				state = _State.TURN
				continue

			river_m = RIVER_RE.search(line)
			if river_m:
				river = Street(cards=[to_card(river_m.group(5))])
				current_actions = river.actions
				state = _State.RIVER
				continue

			if "SHOWDOWN" in line:
				state = _State.SHOWDOWN
				continue

			if "SUMMARY" in line:
				state = _State.SUMMARY
				continue

			continue

		# ---- SEATS: player seats + blind posts ----
		if state == _State.SEATS:
			seat_m = SEAT_STACK_RE.search(line)
			if seat_m:
				players.append((seat_m.group(2), int(seat_m.group(1)), float(seat_m.group(3))))
				continue
			blind_m = BLIND_POST_RE.search(line)
			if blind_m:
				blinds.append(BlindPost(
					player=blind_m.group(1),
					amount=float(blind_m.group(3)),
					is_small=blind_m.group(2) == "small",
					is_hero=blind_m.group(1) == "Hero",
				))
			continue

		# ---- HOLE_CARDS: dealt cards, then transition to preflop on first action ----
		if state == _State.HOLE_CARDS:
			hero_m = DEALT_HERO_RE.search(line)
			if hero_m:
				hero_hole_cards = to_hole_cards(hero_m.group(1), hero_m.group(2))
				continue
			# Non-dealt line (e.g. "Dealt to 43f91dd2") — skip unless it's an action
			action_m = ACTION_RE.search(line)
			if action_m:
				state = _State.PREFLOP
				current_actions.append(_parse_action(line, action_m))
			continue

		# ---- Action states: PREFLOP / FLOP / TURN / RIVER ----
		if state in (_State.PREFLOP, _State.FLOP, _State.TURN, _State.RIVER):
			# Uncalled bet
			unc_m = UNCALLED_FULL_RE.search(line)
			if unc_m:
				uncalled_amount = float(unc_m.group(1))
				uncalled_to = unc_m.group(2).strip()
				continue

			action_m = ACTION_RE.search(line)
			if action_m:
				current_actions.append(_parse_action(line, action_m))
			continue

		# ---- SHOWDOWN: collected lines ----
		if state == _State.SHOWDOWN:
			coll_m = HERO_COLLECTED_RE.search(line)
			if coll_m:
				hero_collected += float(coll_m.group(1))
			continue

		# ---- SUMMARY: total pot, hero showdown result ----
		if state == _State.SUMMARY:
			pot_m = TOTAL_POT_RE.search(line)
			if pot_m:
				total_pot = float(pot_m.group(1))
				continue
			show_m = HERO_SHOWDOWN_RE.search(line)
			if show_m:
				hero_showed_won = show_m.group(1) == "won"
				won_m = HERO_WON_RE.search(line)
				if won_m:
					hero_collected = float(won_m.group(1))
			continue

	return HandAST(
		hand_id=hand_id,
		played_on=played_on,
		button_seat=button_seat,
		players=players,
		hero_hole_cards=hero_hole_cards,
		blinds=blinds,
		preflop=preflop,
		flop=flop,
		turn=turn,
		river=river,
		hero_collected=hero_collected,
		total_pot=total_pot,
		uncalled_amount=uncalled_amount,
		uncalled_to=uncalled_to,
		hero_showed_won=hero_showed_won,
	)
