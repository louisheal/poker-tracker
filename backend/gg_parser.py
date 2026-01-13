import re

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards


DEALT_RE = re.compile(r"Dealt to\s+Hero\s*\[([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\]", re.IGNORECASE)
SUMMARY_RE = re.compile(r"^\*\*\*\s*SUMMARY\s*\*\*\*")


class Parser:

	def __init__(self):
		self.hands: list[HoleCards] = []
		self.current_hole_cards: HoleCards | None = None

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
		
		if SUMMARY_RE.match(text):
			if self.current_hole_cards is not None:
				self.hands.append(self.current_hole_cards)
			self.current_hole_cards = None

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

	print(f'Parsed {len(p.hands)} hero hole cards:')
	for i, hc in enumerate(p.hands, 1):
		fst = hc.fst_card.to_json()
		snd = hc.snd_card.to_json()
		print(f'{i}: {fst["Rank"]}{fst["Suit"]} {snd["Rank"]}{snd["Suit"]}')


if __name__ == '__main__':
	main()
