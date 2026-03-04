import re
from typing import Generator

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards, PokerPosition, PotType, PokerAction, BoardType
from models import Ranges, CBets

START_RE = re.compile(r"Poker Hand #(.*): .*")
DEALT_HERO_RE = re.compile(r"Dealt to\s+Hero\s*\[([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\]", re.IGNORECASE)
ACTION_RE = re.compile(r"(.*): (folds|calls|raises|checks|bets)\b", re.IGNORECASE)
SUMMARY_RE = re.compile(r"^\*\*\*\s*SUMMARY\s*\*\*\*")
FLOP_RE = re.compile(r"\*\*\* FLOP \*\*\* \[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\]", re.IGNORECASE)

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

def parse_histories(files: list[str]) -> Ranges:
	ranges = Ranges()
	cbets = CBets()
	pot_type = None

	for file in files:
		for hand in group_hands(file):
			hole_cards, position, actions = parse_hand(hand)
			if not hole_cards:
				continue
			for action, pot_type, villain in actions:
				ranges.add_hand(hole_cards.key(), position, action, pot_type, villain)
				pot_type = pot_type
	
	return ranges

def group_hands(file):
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
				yield curr_hand
				in_hand = False

def parse_hand(lines: list[str]):
	hole_cards = parse_hero_hole_cards(lines)
	position = parse_hero_position(lines)
	hero_actions = parse_hero_actions(lines)
	return hole_cards, position, hero_actions

# class CBetEvent:
# 	pot_type: PotType
# 	board_type: BoardType
# 	hero_preflop_raiser: bool
# 	hero_in_position: bool
# 	cbet: bool
# 	fold_to_cbet: bool

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
		

def parse_hero_actions(lines: list[str]) -> Generator[tuple[PokerAction, PotType, PokerPosition | None]]:
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
