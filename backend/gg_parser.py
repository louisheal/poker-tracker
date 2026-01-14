import re

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards


DEALT_RE = re.compile(r"Dealt to\s+Hero\s*\[([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\]", re.IGNORECASE)
SUMMARY_RE = re.compile(r"^\*\*\*\s*SUMMARY\s*\*\*\*")
FLOP_RE = re.compile(r"^\*\*\* FLOP \*\*\*\s*\[([^\]]+)\]", re.IGNORECASE)



class Parser:

	def __init__(self):
		self.hands: list[dict] = []
		self.current_hole_cards: HoleCards | None = None
		self.current_flop_cards: list[Card] | None = None

	def next(self, line: str) -> None:
		text = line.strip()
		if not text:
			return
		
		match = DEALT_RE.search(text)
		if match:
			fst_card = self._token_to_card(match.group(1))
			snd_card = self._token_to_card(match.group(2))
			self.current_hole_cards = HoleCards(fst_card, snd_card)
			return

		flop_m = FLOP_RE.search(text)
		if flop_m:
			cards_text = flop_m.group(1)
			toks = re.split(r"[\s,]+", cards_text.strip())
			cards = []
			for tok in toks:
				if not tok:
					continue
				cards.append(self._token_to_card(tok))
			self.current_flop_cards = cards
			return
		
		if SUMMARY_RE.match(text):
			if self.current_hole_cards is not None:
				hand = {
					'hole': self.current_hole_cards,
					'flop': self.current_flop_cards if self.current_flop_cards is not None else []
				}
				self.hands.append(hand)
			self.current_hole_cards = None
			self.current_flop_cards = None

	def _token_to_card(self, token: str) -> Card:
		t = token.strip()
		rank_token = t[0].upper()
		suit_token = t[1].upper()
		rank = Rank(rank_token)
		suit = Suit(suit_token)
		return Card(rank, suit)


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
		fst = hc.fst_card.to_json()
		snd = hc.snd_card.to_json()
		flop_str = ' '.join(f"{c.rank.value}{c.suit.value}" for c in flop) if flop else '(no flop)'
		print(f'{i}: {fst["Rank"]}{fst["Suit"]} {snd["Rank"]}{snd["Suit"]}  |  Flop: {flop_str}')


if __name__ == '__main__':
	main()
