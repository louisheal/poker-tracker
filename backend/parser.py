from datetime import date, datetime
import re
from typing import Generator

from models import CBetEvent, RangeEvent
from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import BoardType, HoleCards, PokerPosition, PotType

START_RE = re.compile(r"^Poker Hand #[^:]+: .* - (\d{4}/\d{2}/\d{2}) \d{2}:\d{2}:\d{2}$")
DEALT_HERO_RE = re.compile(r"Dealt to\s+Hero\s*\[([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\]", re.IGNORECASE)
ACTION_RE = re.compile(r"(.*): (folds|calls|raises|checks|bets)\b", re.IGNORECASE)
SUMMARY_RE = re.compile(r"^\*\*\*\s*SUMMARY\s*\*\*\*")
FLOP_RE = re.compile(r"\*\*\* FLOP \*\*\* \[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\]", re.IGNORECASE)
SEAT_RE = re.compile(r"^Seat\s+\d+:\s+([^\s]+)")

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

def parse_histories(files: list[str]) -> tuple[list[RangeEvent], list[CBetEvent]]:
	range_events: list[RangeEvent] = []
	cbet_events: list[CBetEvent] = []
	include_multiway = False

	for file in files:
		for hand in group_hands(file, include_multiway):
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

	return range_events, cbet_events


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
	in_hand = True

	with open(file, 'r', encoding='utf-8') as f:
		for line in f:
			text = line.strip()
			if not text:
				continue

			if "Poker Hand" in text:
				in_hand = True
				curr_hand = []

			if not in_hand:
				continue

			curr_hand.append(text)

			if text == "*** SUMMARY ***":
				if include_multiway:
					yield curr_hand
				else:
					players_on_flop = flop_player_count(curr_hand)
					if players_on_flop is None or players_on_flop <= 2:
						yield curr_hand
				in_hand = False

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


def parse_flop_cbet(lines: list[str], hero_is_pfr: bool) -> tuple[bool, bool, bool, bool]:

	in_flop = False
	cbet = False
	fold_to_cbet = False
	donk_bet = False
	fold_to_donk_bet = False

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
			fold_to_cbet = act == "folds"
			return cbet, fold_to_cbet, donk_bet, fold_to_donk_bet
		
		if donk_bet and pfr_actor:
			fold_to_donk_bet = act == "folds"
			return cbet, fold_to_cbet, donk_bet, fold_to_donk_bet
		
		if cbet or donk_bet:
			continue

		if pfr_actor and act == "bets":
			cbet = True
			continue

		if not pfr_actor and act == "bets":
			donk_bet = True
			continue
	
	return cbet, fold_to_cbet, donk_bet, fold_to_donk_bet


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
	event.cbet, event.fold_to_cbet, event.donk_bet, event.fold_to_donk_bet = parse_flop_cbet(lines, event.hero_preflop_raiser)
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
