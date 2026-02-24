import re

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards

START_RE = re.compile(r"Poker Hand #(.*): .*")
DEALT_HERO_RE = re.compile(r"Dealt to\s+Hero\s*\[([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\]", re.IGNORECASE)
ACTION_RE = re.compile(r"(.*): (folds|calls|raises|checks)\b", re.IGNORECASE)
SUMMARY_RE = re.compile(r"^\*\*\*\s*SUMMARY\s*\*\*\*")

POSITIONS = ["LJ", "HJ", "CO", "BTN", "SB", "BB"]

class Stats:
	def __init__(self, folds: int, calls: int, raises: int, checks: int):
		self.folds = folds
		self.calls = calls
		self.raises = raises
		self.checks = checks

class Range:
	def __init__(self):
		self.hands: dict[str, Stats] = self._initialise_hands()

	def add(self, hole_cards: HoleCards, action: str):
		key = hole_cards.to_key()
		if key not in self.hands:
			print(f"Error: unknown hole cards {hole_cards}")
			return
		
		stats = self.hands[key]
		if action.lower() == "folds":
			stats.folds += 1
		elif action.lower() == "raises":
			stats.raises += 1
		else:
			print(f"Error: unknown action {action}")

	def _initialise_hands(self):
		hands = {}
		for fst_rank in Rank:
			for snd_rank in Rank:
				for fst_suit in Suit:
					for snd_suit in Suit:
						fst_card = Card(fst_rank, fst_suit)
						snd_card = Card(snd_rank, snd_suit)
						hole_cards = HoleCards(fst_card, snd_card)
						hands[hole_cards.to_key()] = Stats(0, 0, 0, 0)
		return hands

# Find "Dealt to Hero [.. ..]"
# After all "Dealt to"s the actions start
# Continue while not "Hero: {action}" or "villain: {not folds}"

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

class Parser:

	def __init__(self, ranges: dict[str, Range]):
		self.ranges = ranges
		self.hole_cards: HoleCards | None = None
		self.position: str | None = None
		self.action: str | None = None
		self.i: int = 0
		self.skip = False

	def next(self, line: str) -> None:
		text = line.strip()
		if not text:
			return
		
		if self.skip and text == "*** SUMMARY ***":
			self.skip = False
			return
		
		if START_RE.match(text):
			self.hole_cards = None
			self.position = None
			self.action = None
			self.i = 0
			self.in_hand = False
			return

		if self.hole_cards is None:

			hole_cards = DEALT_HERO_RE.search(text)
			if not hole_cards:
				return
			
			self.hole_cards = parse_hole_cards(hole_cards)
			return
		
		if not self.position:

			action = ACTION_RE.search(text)
			if not action:
				return

			if action.group(1).lower() != "hero":
				if action.group(2).lower() != "folds":
					self.skip = True
					return

				self.i += 1
				return
			
			if (self.i > 5):
				raise Exception("Error: reached hero's action after 5 lines of actions, likely an error in parsing")
			
			self.position = POSITIONS[self.i]
			self.action = action.group(2)
			return
		
		if text != "*** SUMMARY ***":
			return
		
		if self.hole_cards is None:
			print("Error: reached end of hand without finding hole cards")
			return

		if self.position is None:
			print("Error: reached end of hand without finding hero's position")
			return

		self.ranges[self.position].add(self.hole_cards, self.action)
