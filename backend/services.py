import json
import uuid

from playing_cards_lib import Rank
from playing_cards_lib.poker import PokerDealer, PokerHand

from dto import HandDto
from fastapi import HTTPException, status

def all_hand_combos():
    result = []
    for a in list(Rank)[::-1]:
        row = []
        for b in list(Rank)[::-1]:
            if a < b:
                row.append(f"{b.value}{a.value}o")
            elif a > b:
                row.append(f"{a.value}{b.value}s")
            else:
                row.append(f"{a.value}{b.value}")
        result.append(row)
    return result

all_hands = all_hand_combos()

class HandTracker():
    def __init__(self):
        self.ranges: list[dict[str, dict[str, int]]] = [{} for _ in range(6)]

    def fold(self, pos: int, hand: PokerHand):
        if hand.to_key() not in self.ranges[pos]:
            self.ranges[pos][hand.to_key()] = {"folds": 0, "raises": 0}
        self.ranges[pos][hand.to_key()]["folds"] += 1

    def raise_(self, pos: int, hand: PokerHand):
        if hand.to_key() not in self.ranges[pos]:
            self.ranges[pos][hand.to_key()] = {"folds": 0, "raises": 0}
        self.ranges[pos][hand.to_key()]["raises"] += 1

    def get_range(self, pos: int):
        result = []
        for row in all_hands:
            range_row = []
            for combo in row:
                if combo in self.ranges[pos]:
                    entry = self.ranges[pos][combo]
                    entry["key"] = combo
                    range_row.append(entry)
                else:
                    range_row.append({"key": combo, "folds": 0, "raises": 0})
            result.append(range_row)
        return result
    
class GtoRanges():
    paths = [
        "ranges/sb_open.json",
        "ranges/sb_open.json",
        "ranges/btn_open.json",
        "ranges/co_open.json",
        "ranges/hj_open.json",
        "ranges/lj_open.json",
    ]

    def __init__(self):
        self.ranges: list[dict[str, str]] = []
        for path in self.paths:
            with open(path, "r") as f:
                data = f.read()
            self.ranges.append(json.loads(data))

    def get_range(self, pos: int):
        result = []
        for row in all_hands:
            range_row = []
            for combo in row:
                entry = {"key": combo}
                if combo in self.ranges[pos]:
                    entry["folds"] = 1 if self.ranges[pos][combo] == "Fold" else 0
                    entry["raises"] = 1 if self.ranges[pos][combo] == "Raise" else 0
                range_row.append(entry)
            result.append(range_row)
        return result
    
    def is_correct(self, pos: int, hand: PokerHand, action: str):
        expected = self.ranges[pos].get(hand.to_key(), "Fold")
        return expected == action

class PokerService():
    def __init__(self, dealer: PokerDealer, tracker: HandTracker, gto: GtoRanges):
        self.dealer = dealer
        self.tracker = tracker
        self.gto = gto
        self.hands: dict[str, PokerHand] = {}

    def deal_hand(self):
        self.dealer.reset()
        hand = self.dealer.deal_preflop(num_players=6)[0]
        corr_id = str(uuid.uuid4())
        self.hands[corr_id] = hand
        return HandDto(corr_id, hand)

    def fold_hand(self, id: str, pos: int):
        hand = self.hands.pop(id, None)
        if not hand:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hand not found")
        self.tracker.fold(pos, hand)
        return self.gto.is_correct(pos, hand, "Fold")

    def raise_hand(self, id: str, pos: int):
        hand = self.hands.pop(id, None)
        if not hand:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hand not found")
        self.tracker.raise_(pos, hand)
        return self.gto.is_correct(pos, hand, "Raise")

    def get_ranges(self, pos: int):
        return {
            "played": self.tracker.get_range(pos),
            "gto": self.gto.get_range(pos)
        }