import logging
import re
from dataclasses import dataclass, field
from datetime import date

from playing_cards_lib.poker import PokerPosition
from app.models.events import RangeEvent, FlopEvent, TurnEvent, RiverEvent, LineEvent

from .lexer import lex_hand, SEAT_STACK_RE
from .analyzers import build_context, analyze_range, analyze_cbet, analyze_turn, analyze_river, analyze_line, _get_flop_players

logger = logging.getLogger(__name__)

FLOP_RE = re.compile(r"\*\*\* FLOP \*\*\* \[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\]", re.IGNORECASE)
ACTION_RE = re.compile(r"(.*): (folds|calls|raises|checks|bets)\b", re.IGNORECASE)
START_RE = re.compile(r"^Poker Hand #[^:]+: .* - (\d{4}/\d{2}/\d{2}) \d{2}:\d{2}:\d{2}$")


def parse_hand_date(lines: list[str]) -> date | None:
	from datetime import datetime
	for line in lines:
		m = START_RE.search(line)
		if not m:
			continue
		return datetime.strptime(m.group(1), "%Y/%m/%d").date()
	return None


def flop_player_count(lines: list[str]) -> int | None:
	players: set[str] = set()
	for line in lines:
		seat = SEAT_STACK_RE.search(line)
		if seat:
			players.add(seat.group(2))

	active_players = set(players)
	for line in lines:
		if FLOP_RE.search(line):
			return len(active_players)
		action = ACTION_RE.search(line)
		if not action:
			continue
		if action.group(2).lower() == "folds":
			active_players.discard(action.group(1))
	return None


def group_hands(file, include_multiway: bool = False):
	curr_hand = []

	with open(file, 'r', encoding='utf-8') as f:
		for line in f:
			text = line.strip()
			if not text:
				if curr_hand:
					if include_multiway:
						yield curr_hand
					else:
						players_on_flop = flop_player_count(curr_hand)
						if players_on_flop is None or players_on_flop <= 2:
							yield curr_hand
					curr_hand = []
				continue

			if "Poker Hand" in text and curr_hand:
				if include_multiway:
					yield curr_hand
				else:
					players_on_flop = flop_player_count(curr_hand)
					if players_on_flop is None or players_on_flop <= 2:
						yield curr_hand
				curr_hand = []

			curr_hand.append(text)

	if curr_hand:
		if include_multiway:
			yield curr_hand
		else:
			players_on_flop = flop_player_count(curr_hand)
			if players_on_flop is None or players_on_flop <= 2:
				yield curr_hand


def parse_histories(files: list[str]) -> tuple[list[RangeEvent], list[FlopEvent], list[TurnEvent], list[RiverEvent], list[LineEvent]]:
	combined = FileParseResult()
	for file in files:
		result = parse_file(file)
		combined.merge(result)
	logger.info(f"Parsing complete. Total hands: {combined.hand_count}")
	return combined.range_events, combined.cbet_events, combined.turn_events, combined.river_events, combined.line_events


@dataclass
class FileParseResult:
	"""All events and metadata parsed from a single hand history file."""
	range_events: list[RangeEvent] = field(default_factory=list)
	cbet_events: list[FlopEvent] = field(default_factory=list)
	turn_events: list[TurnEvent] = field(default_factory=list)
	river_events: list[RiverEvent] = field(default_factory=list)
	line_events: list[LineEvent] = field(default_factory=list)
	hand_dates: list[date] = field(default_factory=list)
	hand_count: int = 0

	def merge(self, other: "FileParseResult"):
		self.range_events.extend(other.range_events)
		self.cbet_events.extend(other.cbet_events)
		self.turn_events.extend(other.turn_events)
		self.river_events.extend(other.river_events)
		self.line_events.extend(other.line_events)
		self.hand_dates.extend(other.hand_dates)
		self.hand_count += other.hand_count


def parse_file(file: str) -> FileParseResult:
	"""Parse a single hand history file into events."""
	result = FileParseResult()

	for hand in group_hands(file, include_multiway=True):
		ast = lex_hand(hand)
		if ast is None:
			continue

		result.hand_dates.append(ast.played_on)

		players_on_flop = flop_player_count(hand)
		if players_on_flop is not None and players_on_flop > 2:
			continue

		result.hand_count += 1

		ctx = build_context(ast)

		result.range_events.extend(analyze_range(ast))

		cbet_event = analyze_cbet(ctx)
		if cbet_event:
			result.cbet_events.append(cbet_event)

		turn_event = analyze_turn(ctx)
		if turn_event:
			result.turn_events.append(turn_event)

		river_event = analyze_river(ctx)
		if river_event:
			result.river_events.append(river_event)

		line_event = analyze_line(ctx)
		if line_event:
			result.line_events.append(line_event)

		# Pool events: when hero didn't see flop, generate from each player's perspective
		if not ctx.hero_sees_flop and ast.flop is not None:
			pool_players = _get_flop_players(ast)
			if len(pool_players) == 2:
				for player in pool_players:
					pool_ctx = build_context(ast, player=player)
					pool_cbet = analyze_cbet(pool_ctx)
					if pool_cbet:
						pool_cbet.is_pool = True
						result.cbet_events.append(pool_cbet)
					pool_turn = analyze_turn(pool_ctx)
					if pool_turn:
						pool_turn.is_pool = True
						result.turn_events.append(pool_turn)
					pool_river = analyze_river(pool_ctx)
					if pool_river:
						pool_river.is_pool = True
						result.river_events.append(pool_river)
					pool_line = analyze_line(pool_ctx)
					if pool_line:
						pool_line.is_pool = True
						result.line_events.append(pool_line)

	return result


def parse_hand_dates(files: list[str]) -> list[date]:
	"""Deprecated: use parse_file() results instead. Kept for backwards compat."""
	hand_dates: list[date] = []
	for file in files:
		for hand in group_hands(file, include_multiway=True):
			played_on = parse_hand_date(hand)
			if played_on is None:
				continue
			hand_dates.append(played_on)
	return hand_dates
