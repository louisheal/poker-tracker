import logging
from datetime import date

from app.models.events import RangeEvent, CBetEvent, TurnEvent, RiverEvent, LineEvent

from .common import group_hands, parse_hand_date
from .lexer import lex_hand
from .analyzers import build_context, analyze_range, analyze_cbet, analyze_turn, analyze_river, analyze_line

logger = logging.getLogger(__name__)


def parse_histories(files: list[str]) -> tuple[list[RangeEvent], list[CBetEvent], list[TurnEvent], list[RiverEvent], list[LineEvent]]:
	range_events: list[RangeEvent] = []
	cbet_events: list[CBetEvent] = []
	turn_events: list[TurnEvent] = []
	river_events: list[RiverEvent] = []
	line_events: list[LineEvent] = []
	hand_count = 0

	for file in files:
		for hand in group_hands(file, include_multiway=False):
			hand_count += 1
			if hand_count % 1000 == 0:
				logger.info(f"Parsed {hand_count} hands...")

			ast = lex_hand(hand)
			if ast is None:
				continue

			ctx = build_context(ast)

			range_events.extend(analyze_range(ast))

			cbet_event = analyze_cbet(ctx)
			if cbet_event:
				cbet_events.append(cbet_event)

			turn_event = analyze_turn(ctx)
			if turn_event:
				turn_events.append(turn_event)

			river_event = analyze_river(ctx)
			if river_event:
				river_events.append(river_event)

			line_event = analyze_line(ctx)
			if line_event:
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
