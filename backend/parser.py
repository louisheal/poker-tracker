import re

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards, PokerPosition
from models import RfiRanges

START_RE = re.compile(r"Poker Hand #(.*): .*")
DEALT_HERO_RE = re.compile(r"Dealt to\s+Hero\s*\[([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\]", re.IGNORECASE)
ACTION_RE = re.compile(r"(.*): (folds|calls|raises|checks)\b", re.IGNORECASE)
SUMMARY_RE = re.compile(r"^\*\*\*\s*SUMMARY\s*\*\*\*")

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

def parse_histories(files: list[str]) -> RfiRanges:
	ranges = RfiRanges()

	for file in files:
		for hand in parse_hands(file):
			hole_cards, position, action, rfi = parse_hand(hand)
			if not rfi or position == PokerPosition.BB:
				continue
			ranges.add_hand(hole_cards.to_key(), position, action)
	
	return ranges

def parse_hands(file):
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
	action = parse_hero_action(lines)
	rfi = is_hand_rfi_decision(lines)

	return hole_cards, position, action, rfi

def is_hand_rfi_decision(lines: list[str]):
	for line in lines:
		action = ACTION_RE.search(line)
		if not action:
			continue
		if action.group(2) != "folds":
			return action.group(1) == "Hero"
	return True

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

def parse_hero_action(lines: list[str]):
	for line in lines:
		action = ACTION_RE.search(line)
		if not action:
			continue
		if action.group(1) == "Hero":
			return action.group(2)
