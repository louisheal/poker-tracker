import logging
from datetime import date, datetime
import re
from typing import Generator

from models import CBetEvent, FlopActionSequence, FlopRankTexture, RangeEvent, RiverActionSequence, RiverEvent, RiverRunout, ShowdownType, TurnActionSequence, TurnEvent, TurnRunout

logger = logging.getLogger(__name__)
from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import BoardType, HoleCards, PokerPosition, PotType

START_RE = re.compile(r"^Poker Hand #[^:]+: .* - (\d{4}/\d{2}/\d{2}) \d{2}:\d{2}:\d{2}$")
DEALT_HERO_RE = re.compile(r"Dealt to\s+Hero\s*\[([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\]", re.IGNORECASE)
ACTION_RE = re.compile(r"(.*): (folds|calls|raises|checks|bets)\b", re.IGNORECASE)
SUMMARY_RE = re.compile(r"^\*\*\*\s*SUMMARY\s*\*\*\*")
FLOP_RE = re.compile(r"\*\*\* FLOP \*\*\* \[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\]", re.IGNORECASE)
TURN_RE = re.compile(r"\*\*\* TURN \*\*\* \[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\] \[([2-9TJQKA][shdc])\]", re.IGNORECASE)
RIVER_RE = re.compile(r"\*\*\* RIVER \*\*\* \[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\] \[([2-9TJQKA][shdc])\]", re.IGNORECASE)
TOTAL_POT_RE = re.compile(r"Total pot \$(\d+\.?\d*)")
HERO_SHOWDOWN_RE = re.compile(r"Hero.*showed.*and (won|lost)")
SEAT_RE = re.compile(r"^Seat\s+\d+:\s+([^\s]+)")
BLIND_RE = re.compile(r"posts (?:small|big) blind \$(\d+\.?\d*)")
BET_AMOUNT_RE = re.compile(r": bets \$(\d+\.?\d*)")
CALL_AMOUNT_RE = re.compile(r": calls \$(\d+\.?\d*)")
RAISE_TO_AMOUNT_RE = re.compile(r": raises \$[\d.]+ to \$(\d+\.?\d*)")
UNCALLED_RE = re.compile(r"Uncalled bet \(\$(\d+\.?\d*)\)")

def to_card(token: str) -> Card:
	t = token.strip()
	rank_token = t[0].upper()
	suit_token = t[1].upper()
	rank = Rank(rank_token)
	suit = Suit(suit_token)
	return Card(rank, suit)

def to_hole_cards(fst: str, snd: str) -> HoleCards:
	fst_card = to_card(fst)
	snd_card = to_card(snd)
	return HoleCards(fst_card, snd_card)

def parse_histories(files: list[str]) -> tuple[list[RangeEvent], list[CBetEvent], list[TurnEvent], list[RiverEvent]]:
	range_events: list[RangeEvent] = []
	cbet_events: list[CBetEvent] = []
	turn_events: list[TurnEvent] = []
	river_events: list[RiverEvent] = []
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

	logger.info(f"Parsing complete. Total hands: {hand_count}")
	return range_events, cbet_events, turn_events, river_events


def parse_hand_dates(files: list[str]) -> list[date]:
	hand_dates: list[date] = []
	for file in files:
		for hand in group_hands(file, include_multiway=True):
			played_on = parse_hand_date(hand)
			if played_on is None:
				continue
			hand_dates.append(played_on)
	return hand_dates


def parse_hand_date(lines: list[str]) -> date | None:
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

def parse_hand(lines: list[str]):
	hole_cards = parse_hero_hole_cards(lines)
	position = parse_hero_position(lines)
	hero_actions = parse_hero_actions(lines)
	return hole_cards, position, hero_actions

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


def parse_turn_action_sequence(lines: list[str]) -> TurnActionSequence | None:
	in_turn = False
	sequence = ""

	for line in lines:
		if TURN_RE.search(line):
			in_turn = True
			continue

		if not in_turn:
			continue

		if any(m in line for m in ["*** RIVER ***", "*** SHOWDOWN ***", "*** SUMMARY ***"]):
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

	if sequence == "XX":
		return TurnActionSequence.XX
	elif sequence == "XBC":
		return TurnActionSequence.XBC
	elif sequence == "XBRC":
		return TurnActionSequence.XBRC
	elif sequence == "BC":
		return TurnActionSequence.BC

	return None


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


def parse_turn_actions(lines: list[str]) -> tuple[bool, bool, bool, bool, bool, bool]:
	in_turn = False
	hero_bet_turn = False
	villain_fold_to_hero_bet = False
	villain_raise_to_hero_bet = False
	villain_bet_turn = False
	hero_fold_to_villain_bet = False
	hero_raise_to_villain_bet = False
	
	for line in lines:
		if TURN_RE.search(line):
			in_turn = True
			continue
		
		if not in_turn:
			continue
		
		if any(m in line for m in ["*** RIVER ***", "*** SHOWDOWN ***", "*** SUMMARY ***"]):
			break
		
		action = ACTION_RE.search(line)
		if not action:
			continue
		
		actor = action.group(1)
		act = action.group(2).lower()
		
		if hero_bet_turn and actor != "Hero":
			if act == "folds":
				villain_fold_to_hero_bet = True
			elif act == "raises":
				villain_raise_to_hero_bet = True
			# Stop after first response
			return hero_bet_turn, villain_fold_to_hero_bet, villain_raise_to_hero_bet, villain_bet_turn, hero_fold_to_villain_bet, hero_raise_to_villain_bet
		
		if villain_bet_turn and actor == "Hero":
			if act == "folds":
				hero_fold_to_villain_bet = True
			elif act == "raises":
				hero_raise_to_villain_bet = True
			# Stop after first response
			return hero_bet_turn, villain_fold_to_hero_bet, villain_raise_to_hero_bet, villain_bet_turn, hero_fold_to_villain_bet, hero_raise_to_villain_bet
		
		if not hero_bet_turn and not villain_bet_turn:
			if actor == "Hero" and act == "bets":
				hero_bet_turn = True
			elif actor != "Hero" and act == "bets":
				villain_bet_turn = True
	
	return hero_bet_turn, villain_fold_to_hero_bet, villain_raise_to_hero_bet, villain_bet_turn, hero_fold_to_villain_bet, hero_raise_to_villain_bet


def parse_turn_event(lines: list[str]) -> TurnEvent | None:
	board_type = parse_board_type(lines)
	if board_type is None:
		return None
	if not parse_hero_sees_flop(lines):
		return None
	
	flop_action_sequence = parse_flop_action_sequence(lines, parse_hero_preflop_raiser(lines))
	if flop_action_sequence is None:
		return None
	
	turn_runout = parse_turn_runout(lines)
	if turn_runout is None:
		return None
	
	hero_bet_turn, villain_fold_to_hero_bet, villain_raise_to_hero_bet, villain_bet_turn, hero_fold_to_villain_bet, hero_raise_to_villain_bet = parse_turn_actions(lines)
	
	event = TurnEvent()
	event.pot_type = parse_preflop_pot_type(lines)
	event.board_type = board_type
	event.hero_preflop_raiser = parse_hero_preflop_raiser(lines)
	event.hero_in_position = parse_hero_in_position(lines)
	event.flop_action_sequence = flop_action_sequence
	event.turn_runout = turn_runout
	event.hero_bet_turn = hero_bet_turn
	event.villain_fold_to_hero_bet = villain_fold_to_hero_bet
	event.villain_raise_to_hero_bet = villain_raise_to_hero_bet
	event.villain_bet_turn = villain_bet_turn
	event.hero_fold_to_villain_bet = hero_fold_to_villain_bet
	event.hero_raise_to_villain_bet = hero_raise_to_villain_bet
	return event


def parse_cbet_event(lines: list[str]) -> CBetEvent | None:
	board_type = parse_board_type(lines)
	if board_type is None:
		return None
	if not parse_hero_sees_flop(lines):
		return None
	event = CBetEvent()
	event.pot_type = parse_preflop_pot_type(lines)
	event.board_type = board_type
	event.hero_preflop_raiser = parse_hero_preflop_raiser(lines)
	event.hero_in_position = parse_hero_in_position(lines)
	cbet, fold_to_cbet, raise_to_cbet, donk_bet, fold_to_donk_bet, raise_to_donk_bet, cbet_amount, donk_bet_amount = parse_flop_cbet(lines, event.hero_preflop_raiser)
	event.cbet = cbet
	event.fold_to_cbet = fold_to_cbet
	event.raise_to_cbet = raise_to_cbet
	event.donk_bet = donk_bet
	event.fold_to_donk_bet = fold_to_donk_bet
	event.raise_to_donk_bet = raise_to_donk_bet

	# Compute pot-relative bet sizes
	pot_at_flop = parse_pot_at_flop(lines)
	if pot_at_flop and pot_at_flop > 0:
		pot_dollars = pot_at_flop * 0.02
		if cbet_amount is not None:
			event.cbet_size_pct = (cbet_amount / pot_dollars) * 100
		if donk_bet_amount is not None:
			event.donk_bet_size_pct = (donk_bet_amount / pot_dollars) * 100

	return event


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


def parse_river_event(lines: list[str]) -> RiverEvent | None:
	board_type = parse_board_type(lines)
	if board_type is None:
		return None
	if not parse_hero_sees_flop(lines):
		return None

	has_river = any(RIVER_RE.search(line) for line in lines)
	if not has_river:
		return None

	flop_action_sequence = parse_flop_action_sequence(lines, parse_hero_preflop_raiser(lines))
	if flop_action_sequence is None:
		return None

	flop_rank_texture = parse_flop_rank_texture(lines)
	if flop_rank_texture is None:
		return None

	turn_runout = parse_turn_runout(lines)
	if turn_runout is None:
		return None

	turn_action_sequence = parse_turn_action_sequence(lines)
	if turn_action_sequence is None:
		return None

	river_runout = parse_river_runout(lines)
	if river_runout is None:
		return None

	river_action_sequence = parse_river_action_sequence(lines)
	if river_action_sequence is None:
		return None

	hero_bet, v_fold, v_raise, v_bet, h_fold, h_raise = parse_river_actions(lines)
	went_to_showdown, hero_won, pot_size_bb = parse_showdown_result(lines)
	showdown_type = parse_river_showdown_type(lines) if went_to_showdown else None

	event = RiverEvent()
	event.pot_type = parse_preflop_pot_type(lines)
	event.board_type = board_type
	event.hero_in_position = parse_hero_in_position(lines)
	event.flop_action_sequence = flop_action_sequence
	event.flop_rank_texture = flop_rank_texture
	event.turn_runout = turn_runout
	event.turn_action_sequence = turn_action_sequence
	event.river_runout = river_runout
	event.river_action_sequence = river_action_sequence
	event.hero_bet_river = hero_bet
	event.villain_fold_to_hero_bet = v_fold
	event.villain_raise_to_hero_bet = v_raise
	event.villain_bet_river = v_bet
	event.hero_fold_to_villain_bet = h_fold
	event.hero_raise_to_villain_bet = h_raise
	event.went_to_showdown = went_to_showdown
	event.showdown_type = showdown_type
	event.hero_won_showdown = hero_won
	event.pot_size_bb = pot_size_bb
	return event
