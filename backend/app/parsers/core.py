import logging
import re
from datetime import date

from playing_cards_lib.poker import PokerPosition
from app.models.events import RangeEvent, FlopEvent, TurnEvent, RiverEvent, LineEvent

from .lexer import lex_hand
from .analyzers import build_context, analyze_range, analyze_cbet, analyze_turn, analyze_river, analyze_line, _get_flop_players

logger = logging.getLogger(__name__)

FLOP_RE = re.compile(r"\*\*\* FLOP \*\*\* \[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\]", re.IGNORECASE)
SEAT_RE = re.compile(r"^Seat\s+\d+:\s+([^\s]+)")
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
		seat = SEAT_RE.search(line)
		if seat:
			players.add(seat.group(1))

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
	range_events: list[RangeEvent] = []
	cbet_events: list[FlopEvent] = []
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

			# Pool events: when hero didn't see flop, generate from each player's perspective
			if not ctx.hero_sees_flop and ast.flop is not None:
				pool_players = _get_flop_players(ast)
				if len(pool_players) == 2:
					for player in pool_players:
						pool_ctx = build_context(ast, player=player)
						pool_cbet = analyze_cbet(pool_ctx)
						if pool_cbet:
							pool_cbet.is_pool = True
							cbet_events.append(pool_cbet)
						pool_turn = analyze_turn(pool_ctx)
						if pool_turn:
							pool_turn.is_pool = True
							turn_events.append(pool_turn)
						pool_river = analyze_river(pool_ctx)
						if pool_river:
							pool_river.is_pool = True
							river_events.append(pool_river)
						pool_line = analyze_line(pool_ctx)
						if pool_line:
							pool_line.is_pool = True
							line_events.append(pool_line)

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
