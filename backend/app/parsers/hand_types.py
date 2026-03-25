from collections import Counter

from playing_cards_lib.core import Card, Rank
from playing_cards_lib.poker import HoleCards
from app.models.enums import MadeHandType, DrawType

RANK_ORDER = list(Rank)
RANK_INDEX = {r: i for i, r in enumerate(RANK_ORDER)}

# Ace-low straight: A-2-3-4-5
ACE_LOW_STRAIGHT_RANKS = {Rank.ACE, Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE}


def _rank_value(rank: Rank) -> int:
	return RANK_INDEX[rank]


def _has_straight(rank_set: set[Rank]) -> bool:
	"""Check if 5+ ranks form a straight (including ace-low)."""
	if len(rank_set) < 5:
		return False
	if ACE_LOW_STRAIGHT_RANKS.issubset(rank_set):
		return True
	indices = sorted(_rank_value(r) for r in rank_set)
	consecutive = 1
	for i in range(1, len(indices)):
		if indices[i] == indices[i - 1] + 1:
			consecutive += 1
			if consecutive >= 5:
				return True
		else:
			consecutive = 1
	return False


def _has_flush(suits: list) -> bool:
	"""Check if 5+ cards share the same suit."""
	counts = Counter(suits)
	return any(c >= 5 for c in counts.values())


def _flush_suit(suits: list) -> object | None:
	"""Return the suit with 5+ cards, or None."""
	counts = Counter(suits)
	for suit, count in counts.items():
		if count >= 5:
			return suit
	return None


def _straight_draw_outs(rank_set: set[Rank]) -> tuple[bool, bool]:
	"""Return (is_oesd, is_gutshot) for draws requiring exactly 1 card.

	Only considers draws where we need one more card to make a 5-card straight.
	Does NOT count draws when a straight is already made.
	"""
	if _has_straight(rank_set):
		return False, False

	indices = sorted(set(_rank_value(r) for r in rank_set))

	# Also consider ace as low (index -1 effectively, but we use 0-12 where ace=12)
	# For ace-low draws, we check separately
	oesd = False
	gutshot = False

	# Check all windows of 5 consecutive ranks
	for start in range(-1, 13):
		if start == -1:
			# Ace-low window: A,2,3,4,5 → indices 12,0,1,2,3
			window_indices = [12, 0, 1, 2, 3]
		else:
			window_indices = list(range(start, start + 5))
			if window_indices[-1] > 12:
				continue

		present = sum(1 for wi in window_indices if wi in indices)
		if present == 4:
			# Missing exactly one card → could be OESD or gutshot
			missing_idx = [wi for wi in window_indices if wi not in indices][0]
			# OESD: missing card is at either end of the window
			if missing_idx == window_indices[0] or missing_idx == window_indices[-1]:
				oesd = True
			else:
				gutshot = True

	return oesd, gutshot


def _flush_draw_count(hole_cards: HoleCards, board_cards: list[Card]) -> int:
	"""Return the max number of cards of a single suit including hole cards.

	Returns 4 if we have a flush draw (4 to a flush), 0 otherwise.
	Only counts suits where at least one hole card contributes.
	"""
	all_cards = [hole_cards.fst_card, hole_cards.snd_card] + board_cards
	suit_counts: dict = {}
	hole_suits = {hole_cards.fst_card.suit, hole_cards.snd_card.suit}
	for card in all_cards:
		suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1

	for suit, count in suit_counts.items():
		if count == 4 and suit in hole_suits:
			return 4
	return 0


def classify_made_hand(hole_cards: HoleCards, board_cards: list[Card]) -> MadeHandType:
	"""Classify the best made hand from hole cards + board cards.

	board_cards length determines the street:
	  3 = flop, 4 = turn, 5 = river
	"""
	all_cards = [hole_cards.fst_card, hole_cards.snd_card] + board_cards
	all_ranks = [c.rank for c in all_cards]
	all_suits = [c.suit for c in all_cards]
	rank_counts = Counter(all_ranks)
	board_ranks = [c.rank for c in board_cards]
	board_rank_counts = Counter(board_ranks)
	hole_ranks = {hole_cards.fst_card.rank, hole_cards.snd_card.rank}

	# Check for flush
	flush_s = _flush_suit(all_suits)
	is_flush = flush_s is not None

	# Check for straight
	all_rank_set = set(all_ranks)
	is_straight = _has_straight(all_rank_set)

	# Check for straight flush
	if is_flush and is_straight:
		flush_cards = [c for c in all_cards if c.suit == flush_s]
		flush_rank_set = set(c.rank for c in flush_cards)
		if _has_straight(flush_rank_set):
			return MadeHandType.STRAIGHT_FLUSH

	# Four of a kind
	quads_ranks = [r for r, c in rank_counts.items() if c >= 4]
	if quads_ranks:
		return MadeHandType.QUADS

	# Full house
	trips_ranks = [r for r, c in rank_counts.items() if c >= 3]
	pair_ranks = [r for r, c in rank_counts.items() if c >= 2 and r not in trips_ranks]
	if trips_ranks and (pair_ranks or len(trips_ranks) > 1):
		return MadeHandType.FULL_HOUSE

	if is_flush:
		return MadeHandType.FLUSH

	if is_straight:
		return MadeHandType.STRAIGHT

	# Three of a kind / Set
	if trips_ranks:
		# Check if hero contributes: at least one hole card matches the trips rank
		for tr in trips_ranks:
			if tr in hole_ranks:
				return MadeHandType.SET
		# Board trips, hero doesn't contribute — still trips but categorise as SET
		return MadeHandType.SET

	# Two pair
	all_pairs = [r for r, c in rank_counts.items() if c >= 2]
	if len(all_pairs) >= 2:
		# At least one pair must involve a hole card
		hero_involved = any(r in hole_ranks for r in all_pairs)
		if hero_involved:
			return MadeHandType.TWO_PAIR

	# One pair
	if all_pairs:
		pair_rank = max(all_pairs, key=lambda r: _rank_value(r))
		# Is the pair made with a hole card?
		if pair_rank in hole_ranks:
			board_has_pair_rank = board_rank_counts.get(pair_rank, 0) >= 1
			if board_has_pair_rank:
				# Paired with the board
				top_board_rank = max(board_ranks, key=lambda r: _rank_value(r))
				if pair_rank == top_board_rank:
					return MadeHandType.TOP_PAIR
				else:
					return MadeHandType.PAIR
			else:
				# Pocket pair
				if all(_rank_value(pair_rank) > _rank_value(br) for br in board_ranks):
					return MadeHandType.OVERPAIR
				else:
					return MadeHandType.PAIR
		else:
			# Board pair only, hero doesn't pair — fall through
			pass

	# No pair
	if Rank.ACE in hole_ranks:
		return MadeHandType.ACE_HIGH

	return MadeHandType.NO_MADE_HAND


def classify_draw(hole_cards: HoleCards, board_cards: list[Card]) -> DrawType:
	"""Classify the best draw from hole cards + board cards.

	Only relevant on flop (3 board cards) and turn (4 board cards).
	On the river (5 board cards) there are no draws.
	"""
	if len(board_cards) >= 5:
		return DrawType.NO_DRAW

	has_flush_draw = _flush_draw_count(hole_cards, board_cards) == 4

	all_ranks = {hole_cards.fst_card.rank, hole_cards.snd_card.rank}
	for c in board_cards:
		all_ranks.add(c.rank)

	is_oesd, is_gutshot = _straight_draw_outs(all_ranks)

	if has_flush_draw and is_oesd:
		return DrawType.FLUSH_OESD
	if has_flush_draw and is_gutshot:
		return DrawType.FLUSH_GUTSHOT
	if has_flush_draw:
		return DrawType.FLUSH_DRAW
	if is_oesd:
		return DrawType.OESD
	if is_gutshot:
		return DrawType.GUTSHOT
	return DrawType.NO_DRAW
