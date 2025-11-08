from enum import Enum
from typing import List
import random


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
    

class Deck():

    def __init__(self):
        self.cards = self.__create_deck()

    def reset(self) -> None:
        self.cards = self.__create_deck()

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def draw(self, x: int) -> List[Card]:
        return [self.draw_one() for _ in range(x)]
    
    def draw_one(self) -> Card:
        return self.cards.pop()

    @staticmethod
    def __create_deck() -> List[Card]:
        return [Card(rank, suit) for suit in Suit for rank in Rank]
    