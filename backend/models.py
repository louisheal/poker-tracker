from playing_cards_lib.core import Rank
from playing_cards_lib.poker import PokerPosition


class Stats:
	def __init__(self):
		self.folds = 0
		self.raises = 0

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
				hands[key] = Stats()
		return hands


class RfiRanges:
	def __init__(self):
		self.ranges = {
			PokerPosition.LJ: Range(),
			PokerPosition.HJ: Range(),
			PokerPosition.CO: Range(),
			PokerPosition.BTN: Range(),
			PokerPosition.SB: Range()
        }

	def add_hand(self, hand_key, position, action):
		if position not in self.ranges:
			print(f"Error: invalid rfi position {position}")
		self.ranges[position].add(hand_key, action)
	
	def to_json(self):
		return {k.name: v.to_json() for k, v in self.ranges.items()}