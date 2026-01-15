import re

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards


def token_to_card(token: str) -> Card:
	t = token.strip()
	rank_token = t[0].upper()
	suit_token = t[1].upper()
	rank = Rank(rank_token)
	suit = Suit(suit_token)
	return Card(rank, suit)


DEALT_RE = re.compile(r"Dealt to\s+Hero\s*\[([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\]", re.IGNORECASE)
SUMMARY_RE = re.compile(r"^\*\*\*\s*SUMMARY\s*\*\*\*")
FLOP_RE = re.compile(r"^\*\*\* FLOP \*\*\*\s*\[([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\]", re.IGNORECASE)
TURN_RE = re.compile(r"^\*\*\* TURN \*\*\*\s*\[[^\]]+\]\s*\[([^\]]+)\]", re.IGNORECASE)
RIVER_RE = re.compile(r"^\*\*\* RIVER \*\*\*\s*\[[^\]]+\]\s*\[[^\]]+\]\s*\[([^\]]+)\]", re.IGNORECASE)
HAND_HEADER_RE = re.compile(r"^Poker Hand #")
SMALL_BLIND_RE = re.compile(r"posts small blind \$([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
BIG_BLIND_RE = re.compile(r"posts big blind \$([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)


class Parser:

	def __init__(self):
		self.hands: list[dict] = []
		self.current_hole_cards: HoleCards | None = None
		self.current_flop_cards: tuple[Card, Card, Card] | None = None
		self.current_turn_card: Card | None = None
		self.current_river_card: Card | None = None
		self.pot: int = 0

	def next(self, line: str) -> None:
		text = line.strip()
		if not text:
			return

		small_blind = SMALL_BLIND_RE.search(text)
		if small_blind:
			self._handle_small_blind(small_blind)
			return

		big_blind = BIG_BLIND_RE.search(text)
		if big_blind:
			self._handle_big_blind(big_blind)
			return
		
		hole_cards = DEALT_RE.search(text)
		if hole_cards:
			self._handle_dealt(hole_cards)
			return

		flop_cards = FLOP_RE.search(text)
		if flop_cards:
			self._handle_flop(flop_cards)
			return


		turn_cards = TURN_RE.search(text)
		if turn_cards:
			self._handle_turn(turn_cards)
			return


		river_m = RIVER_RE.search(text)
		if river_m:
			self._handle_river(river_m)
			return
		
		if SUMMARY_RE.match(text):
			if self.current_hole_cards is not None:
				hand = {
					'hole': self.current_hole_cards,
					'flop': self.current_flop_cards if self.current_flop_cards is not None else (),
					'turn': self.current_turn_card,
					'river': self.current_river_card,
					'pot': self.pot
				}
				self.hands.append(hand)
			self.current_hole_cards = None
			self.current_flop_cards = None
			self.current_turn_card = None
			self.current_river_card = None
			self.pot = 0
			return

	def _handle_small_blind(self, match: re.Match) -> None:
		amount = int(float(match.group(1)) * 100)
		self.pot += amount

	def _handle_big_blind(self, match: re.Match) -> None:
		amount = int(float(match.group(1)) * 100)
		self.pot += amount

	def _handle_dealt(self, match: re.Match) -> None:
		fst_card = token_to_card(match.group(1))
		snd_card = token_to_card(match.group(2))
		self.current_hole_cards = HoleCards(fst_card, snd_card)

	def _handle_flop(self, match: re.Match) -> None:
		c1 = token_to_card(match.group(1))
		c2 = token_to_card(match.group(2))
		c3 = token_to_card(match.group(3))
		self.current_flop_cards = (c1, c2, c3)

	def _handle_turn(self, match: re.Match) -> None:
		turn_tok = match.group(1).strip()
		self.current_turn_card = token_to_card(turn_tok)

	def _handle_river(self, match: re.Match) -> None:
		river_tok = match.group(1).strip()
		self.current_river_card = token_to_card(river_tok)


def main():
	import os
	base = os.path.dirname(__file__)
	sample = os.path.join(base, '..', 'GG20260111-2235 - NLHWhite111 - 0.01 - 0.02 - 6max.txt')
	sample = os.path.normpath(sample)
	p = Parser()
	try:
		with open(sample, 'r', encoding='utf-8') as f:
			for line in f:
				p.next(line)
	except FileNotFoundError:
		print('Sample file not found:', sample)
		return

	print(f'Parsed {len(p.hands)} hands:')
	for i, hand in enumerate(p.hands, 1):
		hc = hand['hole']
		flop = hand['flop']
		turn = hand.get('turn')
		river = hand.get('river')
		pot = hand.get('pot', 0.0)
		fst = hc.fst_card.to_json()
		snd = hc.snd_card.to_json()
		if flop and isinstance(flop, (list, tuple)):
			flop_str = ' '.join(f"{c.rank.value}{c.suit.value}" for c in flop)
		else:
			flop_str = '(no flop)'
		turn_str = f"{turn.rank.value}{turn.suit.value}" if turn else '(no turn)'
		river_str = f"{river.rank.value}{river.suit.value}" if river else '(no river)'
		print(f'{i}: {fst["Rank"]}{fst["Suit"]} {snd["Rank"]}{snd["Suit"]}  |  Flop: {flop_str}  |  Turn: {turn_str}  |  River: {river_str}  |  Pot: ${pot/100:.2f}')


if __name__ == '__main__':
	main()
