import logging
from datetime import date
from typing import Generator

from playing_cards_lib.poker import PokerPosition, PotType

from app.models.events import RangeEvent, CBetEvent, TurnEvent, RiverEvent, LineEvent

from .common import group_hands, parse_hand_date, DEALT_HERO_RE, ACTION_RE, to_hole_cards
from .events import parse_cbet_event, parse_turn_event, parse_river_event, parse_line_event
from .preflop import parse_hero_position

logger = logging.getLogger(__name__)


def parse_histories(files: list[str]) -> tuple[list[RangeEvent], list[CBetEvent], list[TurnEvent], list[RiverEvent], list[LineEvent]]:
	range_events: list[RangeEvent] = []
	cbet_events: list[CBetEvent] = []
	turn_events: list[TurnEvent] = []
	river_events: list[RiverEvent] = []
	line_events: list[LineEvent] = []
	include_multiway = False
	hand_count = 0

	for file in files:
		for hand in group_hands(file, include_multiway):
			hand_count += 1
			if hand_count % 1000 == 0:
				logger.info(f"Parsed {hand_count} hands...")
			played_on = parse_hand_date(hand)
			if played_on is None:
				continue
			hole_cards, position, actions = parse_hand(hand)
			if hole_cards:
				for action, pot_type, villain in actions:
					event = RangeEvent()
					event.played_on = played_on
					event.hand_key = hole_cards.key()
					event.position = position
					event.action = action
					event.pot_type = pot_type
					event.villain = villain
					range_events.append(event)
			cbet_event = parse_cbet_event(hand)
			if cbet_event:
				cbet_event.played_on = played_on
				cbet_events.append(cbet_event)
			turn_event = parse_turn_event(hand)
			if turn_event:
				turn_event.played_on = played_on
				turn_events.append(turn_event)
			river_event = parse_river_event(hand)
			if river_event:
				river_event.played_on = played_on
				river_events.append(river_event)
			line_event = parse_line_event(hand)
			if line_event:
				line_event.played_on = played_on
				line_events.append(line_event)

	logger.info(f"Parsing complete. Total hands: {hand_count}")
	return range_events, cbet_events, turn_events, river_events, line_events


def parse_hand_dates(files: list[str]) -> list[date]:
	hand_dates: list[date] = []
	for file in files:
		for hand in group_hands(file, include_multiway=True):
			played_on = parse_hand_date(hand)
			if played_on is None:
				continue
			hand_dates.append(played_on)
	return hand_dates


def parse_hand(lines: list[str]):
	hole_cards = parse_hero_hole_cards(lines)
	position = parse_hero_position(lines)
	hero_actions = parse_hero_actions(lines)
	return hole_cards, position, hero_actions


def parse_hero_actions(lines: list[str]) -> Generator[tuple[str, PotType, PokerPosition | None], None, None]:
	pot_type = PotType.SRP
	v_pos = 0
	villain = None

	for line in lines:
		if "*** FLOP ***" in line:
			return

		action = ACTION_RE.search(line)
		if not action:
			continue

		if action.group(1) == "Hero" and action.group(2) == "checks":
			return

		if action.group(1) != "Hero" and action.group(2) == "folds":
			v_pos += 1
			continue

		if pot_type == PotType.SRP:
			if action.group(1) == "Hero":
				yield (action.group(2), pot_type, None)
				pot_type = PotType.FOUR_BET
				continue
			else:
				villain = PokerPosition(v_pos)
				pot_type = PotType.THREE_BET
				continue

		if pot_type == PotType.THREE_BET:
			if action.group(1) == "Hero":
				yield (action.group(2), pot_type, villain)
				return
			if action.group(2) == "raises":
				pot_type = PotType.FOUR_BET
				continue

		if pot_type == PotType.FOUR_BET:
			if action.group(1) == "Hero":
				yield (action.group(2), pot_type, None)
				return
			if action.group(2) == "raises":
				return

def parse_hero_hole_cards(lines: list[str]):
	for line in lines:
		hole_cards = DEALT_HERO_RE.search(line)
		if not hole_cards:
			continue
		fst = hole_cards.group(1)
		snd = hole_cards.group(2)
		return to_hole_cards(fst, snd)
