import re
from typing import List, Optional
from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import (
	PokerHand, HoleCards, Flop, Turn, River,
	PokerPosition, Bet, Check, Call, Raise, Fold, BetAmount, RaiseMultiplier, PokerAction
)

def parse_rank(rank_str: str) -> Rank:
	return {
		'2': Rank.TWO, '3': Rank.THREE, '4': Rank.FOUR, '5': Rank.FIVE, '6': Rank.SIX,
		'7': Rank.SEVEN, '8': Rank.EIGHT, '9': Rank.NINE, 'T': Rank.TEN, 'J': Rank.JACK,
		'Q': Rank.QUEEN, 'K': Rank.KING, 'A': Rank.ACE
	}[rank_str.upper()]

def parse_suit(suit_str: str) -> Suit:
	return {
		'h': Suit.HEARTS, 'd': Suit.DIAMONDS, 's': Suit.SPADES, 'c': Suit.CLUBS
	}[suit_str.lower()]

def parse_card(card_str: str) -> Card:
	rank = parse_rank(card_str[0])
	suit = parse_suit(card_str[1])
	return Card(rank, suit)

def parse_hole_cards(line: str) -> Optional[List[Card]]:
	m = re.search(r'Dealt to Hero \[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\]', line)
	if m:
		return [parse_card(m.group(1)), parse_card(m.group(2))]
	return None

def parse_board_cards(line: str) -> List[Card]:
	m = re.search(r'\[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\]', line)
	if m:
		return [parse_card(m.group(1)), parse_card(m.group(2)), parse_card(m.group(3))]
	m = re.search(r'\[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\]', line)
	if m:
		return [parse_card(m.group(1)), parse_card(m.group(2)), parse_card(m.group(3)), parse_card(m.group(4))]
	m = re.search(r'\[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\]', line)
	if m:
		return [parse_card(m.group(1)), parse_card(m.group(2)), parse_card(m.group(3)), parse_card(m.group(4)), parse_card(m.group(5))]
	return []

def parse_action(line: str, hero_ip: bool) -> Optional[PokerAction]:
	# Only parse postflop actions, simplified
	# Example: Hero: checks, 4e0ec0e: bets $0.06, Hero: folds
	if 'Hero:' in line:
		pos = PokerPosition.IP if hero_ip else PokerPosition.OOP
		if 'folds' in line:
			return Fold(pos)
		if 'checks' in line:
			return Check(pos)
		if 'calls' in line:
			return Call(pos)
		if 'bets' in line:
			return Bet(pos, BetAmount.MEDIUM_BET)  # Placeholder, refine later
		if 'raises' in line:
			return Raise(pos, RaiseMultiplier.THREE_X)  # Placeholder, refine later
	else:
		pos = PokerPosition.OOP if hero_ip else PokerPosition.IP
		if 'folds' in line:
			return Fold(pos)
		if 'checks' in line:
			return Check(pos)
		if 'calls' in line:
			return Call(pos)
		if 'bets' in line:
			return Bet(pos, BetAmount.MEDIUM_BET)
		if 'raises' in line:
			return Raise(pos, RaiseMultiplier.THREE_X)
	return None

def parse_hand(hand_text: str) -> Optional[PokerHand]:
	lines = hand_text.split('\n')
	hero_hole = None
	for line in lines:
		cards = parse_hole_cards(line)
		if cards:
			hero_hole = HoleCards(cards[0], cards[1])
			break
	if not hero_hole:
		return None

	# Find postflop board
	flop_cards = None
	for line in lines:
		if line.startswith('*** FLOP ***'):
			flop_cards = parse_board_cards(line)
			break
	if not flop_cards:
		return None

	# Determine hero position (simplified: Hero acts first = OOP, else IP)
	postflop_lines = [l for l in lines if l.startswith('*** FLOP ***') or l.startswith('*** TURN ***') or l.startswith('*** RIVER ***')]
	hero_ip = False
	for i, line in enumerate(lines):
		if line.startswith('*** FLOP ***'):
			# Next non-empty action line
			for j in range(i+1, len(lines)):
				if ':' in lines[j]:
					hero_ip = lines[j].startswith('Hero:')
					break
			break

	# Parse actions for each street
	def street_actions(start, end):
		actions = []
		for line in lines[start:end]:
			act = parse_action(line, hero_ip)
			if act:
				actions.append(act)
		return actions

	# Find street indices
	flop_start = None
	turn_start = None
	river_start = None
	for idx, line in enumerate(lines):
		if line.startswith('*** FLOP ***'):
			flop_start = idx
		if line.startswith('*** TURN ***'):
			turn_start = idx
		if line.startswith('*** RIVER ***'):
			river_start = idx

	flop_end = turn_start if turn_start else (river_start if river_start else len(lines))
	turn_end = river_start if river_start else len(lines)

	flop = Flop(flop_cards[0], flop_cards[1], flop_cards[2], street_actions(flop_start+1, flop_end))
	turn = None
	river = None
	if turn_start:
		turn_cards = parse_board_cards(lines[turn_start])
		turn = Turn(turn_cards[3] if len(turn_cards) > 3 else None, street_actions(turn_start+1, turn_end))
	if river_start:
		river_cards = parse_board_cards(lines[river_start])
		river = River(river_cards[4] if len(river_cards) > 4 else None, street_actions(river_start+1, len(lines)))

	hero_pos = PokerPosition.IP if hero_ip else PokerPosition.OOP
	return PokerHand(hero_pos, hero_hole, flop, turn, river)


class GGHandHistoryStatefulParser:
	def __init__(self):
		self.current_hand_lines = []
		self.hands = []

	def feed_line(self, line: str):
		if line.strip() == '':
			if self.current_hand_lines:
				hand_text = '\n'.join(self.current_hand_lines)
				parsed = parse_hand(hand_text)
				if parsed:
					self.hands.append(parsed)
				self.current_hand_lines = []
		else:
			self.current_hand_lines.append(line.rstrip('\n'))

	def finish(self):
		if self.current_hand_lines:
			hand_text = '\n'.join(self.current_hand_lines)
			parsed = parse_hand(hand_text)
			if parsed:
				self.hands.append(parsed)
			self.current_hand_lines = []
		return self.hands

def main():
	import sys
	import json
	if len(sys.argv) < 3:
		print('Usage: python gg_parser.py <hand_history_file> <output_json_file>')
		return
	filename = sys.argv[1]
	outfilename = sys.argv[2]
	parser = GGHandHistoryStatefulParser()
	with open(filename, 'r', encoding='utf-8') as f:
		for line in f:
			parser.feed_line(line)
	hands = parser.finish()
	print(f'Parsed {len(hands)} hands')
	# Convert to JSON-serializable
	def hand_to_json(hand):
		d = {
			'hero_position': hand.hero_position.value,
			'hole_cards': hand.hole_cards.to_json(),
			'flop': {
				'cards': [hand.flop.card1.to_json(), hand.flop.card2.to_json(), hand.flop.card3.to_json()],
				'actions': [type(a).__name__ for a in hand.flop.actions]
			} if hand.flop else None,
			'turn': {
				'card': hand.turn.card.to_json() if hand.turn and hand.turn.card else None,
				'actions': [type(a).__name__ for a in hand.turn.actions] if hand.turn else None
			} if hand.turn else None,
			'river': {
				'card': hand.river.card.to_json() if hand.river and hand.river.card else None,
				'actions': [type(a).__name__ for a in hand.river.actions] if hand.river else None
			} if hand.river else None
		}
		return d
	with open(outfilename, 'w', encoding='utf-8') as outf:
		json.dump([hand_to_json(h) for h in hands], outf, indent=2)

