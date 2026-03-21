import logging

from playing_cards_lib.core import Card
from playing_cards_lib.poker import BoardType

from app.models.enums import TurnRunout, RiverRunout, FlopRankTexture
from .common import FLOP_RE, TURN_RE, RIVER_RE, to_card

logger = logging.getLogger(__name__)


def parse_board_type(lines: list[str]) -> BoardType | None:

	for line in lines:
		flop = FLOP_RE.search(line)
		if not flop:
			continue

		card_one = to_card(flop.group(1))
		card_two = to_card(flop.group(2))
		card_three = to_card(flop.group(3))
		suits = {card_one.suit, card_two.suit, card_three.suit}

		if len(suits) == 3:
			return BoardType.RAINBOW
		elif len(suits) == 2:
			return BoardType.TWO_TONE
		elif len(suits) == 1:
			return BoardType.MONOTONE
	
	return None


def parse_flop_cards(lines: list[str]) -> list[Card] | None:
	for line in lines:
		flop = FLOP_RE.search(line)
		if not flop:
			continue
		return [to_card(flop.group(1)), to_card(flop.group(2)), to_card(flop.group(3))]
	return None


def parse_turn_card(lines: list[str]) -> Card | None:
	for line in lines:
		turn = TURN_RE.search(line)
		if not turn:
			continue
		return to_card(turn.group(4))
	return None


def parse_turn_runout(lines: list[str]) -> TurnRunout | None:
	flop_cards = parse_flop_cards(lines)
	turn_card = parse_turn_card(lines)
	
	if flop_cards is None or turn_card is None:
		return None
	
	flop_ranks = {card.rank for card in flop_cards}
	flop_suits = {card.suit for card in flop_cards}
	
	# Check if turn is an overcard (higher than all flop cards)
	turn_is_overcard = all(turn_card.rank.value > flop_rank.value for flop_rank in flop_ranks)
	if turn_is_overcard:
		return TurnRunout.OVERCARD
	
	# Check if turn pairs with flop
	if turn_card.rank in flop_ranks:
		return TurnRunout.PAIRED
	
	# Check if turn completes flush
	if turn_card.suit in flop_suits:
		flush_suited_flop = sum(1 for card in flop_cards if card.suit == turn_card.suit)
		if flush_suited_flop == 2:
			return TurnRunout.FLUSH_COMPLETING
	
	# Everything else is other
	return TurnRunout.OTHER


def parse_river_card(lines: list[str]) -> Card | None:
	for line in lines:
		river = RIVER_RE.search(line)
		if not river:
			continue
		return to_card(river.group(5))
	return None


def parse_river_runout(lines: list[str]) -> RiverRunout | None:
	flop_cards = parse_flop_cards(lines)
	turn_card = parse_turn_card(lines)
	river_card = parse_river_card(lines)

	if flop_cards is None or turn_card is None or river_card is None:
		return None

	board_ranks = {card.rank for card in flop_cards} | {turn_card.rank}
	board_suits = [card.suit for card in flop_cards] + [turn_card.suit]

	if all(river_card.rank.value > rank.value for rank in board_ranks):
		return RiverRunout.OVERCARD

	if river_card.rank in board_ranks:
		return RiverRunout.PAIRED

	river_suited_count = sum(1 for s in board_suits if s == river_card.suit)
	if river_suited_count >= 2:
		return RiverRunout.FLUSH_COMPLETING

	return RiverRunout.OTHER


def parse_flop_rank_texture(lines: list[str]) -> FlopRankTexture | None:
	flop_cards = parse_flop_cards(lines)
	if flop_cards is None:
		return None

	ranks = [card.rank for card in flop_cards]
	unique_ranks = len(set(ranks))

	if unique_ranks == 1:
		return FlopRankTexture.TRIPS
	elif unique_ranks == 2:
		return FlopRankTexture.PAIRED
	else:
		return FlopRankTexture.UNPAIRED
