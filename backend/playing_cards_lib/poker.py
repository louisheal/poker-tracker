from enum import Enum

from .core import Card


class HoleCards:

    def __init__(self, fst_card: Card, snd_card: Card):
        if fst_card < snd_card:
            fst_card, snd_card = snd_card, fst_card

        self.fst_card = fst_card
        self.snd_card = snd_card

    def json(self):
        return {
            "FstCard": self.fst_card.to_json(),
            "SndCard": self.snd_card.to_json()
        }
    
    def key(self):
        suffix = '' if self.fst_card.rank == self.snd_card.rank else 's' if self.fst_card.suit == self.snd_card.suit else 'o'
        return f"{self.fst_card.rank.value}{self.snd_card.rank.value}{suffix}"

    def __eq__(self, other):
        if not isinstance(other, HoleCards):
            return NotImplemented
        return self.fst_card == other.fst_card and self.snd_card == other.snd_card

    def __hash__(self):
        return hash((self.fst_card, self.snd_card))

    def __repr__(self):
        return f"HoleCards({self.fst_card!r}, {self.snd_card!r})"


class PokerPosition(Enum):
    LJ = 0
    HJ = 1
    CO = 2
    BTN = 3
    SB = 4
    BB = 5
