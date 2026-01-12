from enum import Enum


class Rank(Enum):
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "T"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"

    def __lt__(self, other):
        if not isinstance(other, Rank):
            return NotImplemented
        ranks = list(Rank)
        return ranks.index(self) < ranks.index(other)


class Suit(Enum):
    HEARTS = "H"
    DIAMONDS = "D"
    SPADES = "S"
    CLUBS = "C"


class Card():

    def __init__(self, rank: Rank, suit: Suit):
        self.rank = rank
        self.suit = suit

    def to_json(self):
        return {
            "Rank": self.rank.value,
            "Suit": self.suit.value
        }
    
    def __lt__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank < other.rank
