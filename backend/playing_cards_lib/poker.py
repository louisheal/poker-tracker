from enum import Enum

from .core import Card


class HoleCards:

    def __init__(self, fst_card: Card, snd_card: Card):
        if fst_card < snd_card:
            fst_card, snd_card = snd_card, fst_card

        self.fst_card = fst_card
        self.snd_card = snd_card

    def to_json(self):
        return {
            "FstCard": self.fst_card.to_json(),
            "SndCard": self.snd_card.to_json()
        }
    
    def to_key(self):
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


class BetAmount(Enum):
    SMALL_BET = 1/3
    MEDIUM_BET = 1/2
    LARGE_BET = 3/4
    POT_BET = 1
    OVERBET = 4/3


class RaiseMultiplier(Enum):
    THREE_X = 3
    FOUR_X = 4


class PokerAction:
    def __init__(self, player: PokerPosition):
        self.player = player


class Fold(PokerAction):
    pass

class Check(PokerAction):
    pass


class Bet(PokerAction):
    def __init__(self, amount_bb: BetAmount):
        self.amount_bb = amount_bb


class Call(PokerAction):
    pass


class Raise(PokerAction):
    def __init__(self, raise_multiplier: RaiseMultiplier):
        self.raise_multiplier = raise_multiplier


class Flop:

    def __init__(self, card1: Card, card2: Card, card3: Card, actions: list[PokerAction]):
        self.card1 = card1
        self.card2 = card2
        self.card3 = card3
        self.actions = actions


class Turn:

    def __init__(self, card: Card, actions: list[PokerAction]):
        self.card = card
        self.actions = actions


class River:

    def __init__(self, card: Card, actions: list[PokerAction]):
        self.card = card
        self.actions = actions

class PokerHand:

    def __init__(
            self,
            hero_position: PokerPosition,
            hole_cards: HoleCards,
            flop: Flop,
            turn: Turn | None,
            river: River | None):
        self.hero_position = hero_position
        self.hole_cards = hole_cards
        self.flop = flop
        self.turn = turn
        self.river = river
