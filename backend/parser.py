from enum import Enum
import re

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards

START_RE = re.compile(r"Poker Hand #(.*): .*")
DEALT_HERO_RE = re.compile(r"Dealt to\s+Hero\s*\[([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\]", re.IGNORECASE)
ACTION_RE = re.compile(r"(.*): (folds|calls|raises|checks)\b", re.IGNORECASE)
SUMMARY_RE = re.compile(r"^\*\*\*\s*SUMMARY\s*\*\*\*")

class Position(Enum):
	LJ = 0
	HJ = 1
	CO = 2
	BTN = 3
	SB = 4
	BB = 5

class Stats:
	def __init__(self, folds: int, calls: int, raises: int, checks: int):
		self.folds = folds
		self.calls = calls
		self.raises = raises
		self.checks = checks

	def to_json(self):
		return { "folds": self.folds, "raises": self.raises }

class Range:
	def __init__(self):
		self.hands: dict[str, Stats] = self._initialise_hands()

	def add(self, hand_key: str, action: str):
		if hand_key not in self.hands:
			print(f"Error: unknown hole cards {hand_key}")
			return
		
		stats = self.hands[hand_key]
		if action.lower() == "folds":
			stats.folds += 1
		elif action.lower() == "raises":
			stats.raises += 1
		else:
			print(f"Error: unknown action {action}")

	def to_json(self):
		return { key: stats.to_json() for key, stats in self.hands.items() }

	def _initialise_hands(self):
		hands = {}
		for fst_rank in Rank:
			passed = False
			for snd_rank in Rank:
				key = ""
				if fst_rank == snd_rank:
					key = f"{fst_rank.value}{snd_rank.value}"
					passed = True
				elif passed:
					key = f"{snd_rank.value}{fst_rank.value}s"
				else:
					key = f"{fst_rank.value}{snd_rank.value}o"
				hands[key] = Stats(0, 0, 0, 0)
		return hands

class RfiRanges:
	def __init__(self):
		self.lojack = Range()
		self.hijack = Range()
		self.cutoff = Range()
		self.button = Range()
		self.small_blind = Range()

	def add_hand(self, hand_key, position, action):
		if position == Position.LJ:
			self.lojack.add(hand_key, action)
		elif position == Position.HJ:
			self.hijack.add(hand_key, action)
		elif position == Position.CO:
			self.cutoff.add(hand_key, action)
		elif position == Position.BTN:
			self.button.add(hand_key, action)
		elif position == Position.SB:
			self.small_blind.add(hand_key, action)
		else:
			print(f"Error: invalid rfi position {position}")
	
	def to_json(self):
		return {
			"LJ": self.lojack.to_json(),
			"HJ": self.hijack.to_json(),
			"CO": self.cutoff.to_json(),
			"BTN": self.button.to_json(),
			"SB": self.small_blind.to_json()
		}

def token_to_card(token: str) -> Card:
	t = token.strip()
	rank_token = t[0].upper()
	suit_token = t[1].upper()
	rank = Rank(rank_token)
	suit = Suit(suit_token)
	return Card(rank, suit)

def parse_hole_cards(match: re.Match) -> HoleCards:
	fst_card = token_to_card(match.group(1))
	snd_card = token_to_card(match.group(2))
	return HoleCards(fst_card, snd_card)

def parse_histories(files: list[str]) -> RfiRanges:
	hands = []
	ranges = RfiRanges()

	for file in files:
		curr = parse_hands(file)
		hands += curr
	
	for hand in hands:
		hole_cards, position, action, rfi = parse_hand(hand)
		if not rfi or position == Position.BB:
			continue
		ranges.add_hand(hole_cards.to_key(), position, action)
	
	return ranges

def parse_hands(file) -> list[list[str]]:

	hands = []
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
				hands.append(curr_hand)
				in_hand = False
	
	return hands

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
		if action.group(1) != "Hero" and action.group(2) != "folds":
			return False
	return True

def parse_hero_hole_cards(lines: list[str]):
	for line in lines:
		hole_cards = DEALT_HERO_RE.search(line)
		if not hole_cards:
			continue
		return parse_hole_cards(hole_cards)

def parse_hero_position(lines: list[str]):
	p = 0
	for line in lines:
		action = ACTION_RE.search(line)
		if not action:
			continue
		if action.group(1) == "Hero":
			return Position(p)
		p += 1
	return Position.BB

def parse_hero_action(lines: list[str]):
	for line in lines:
		action = ACTION_RE.search(line)
		if not action:
			continue
		if action.group(1) == "Hero":
			return action.group(2)
