from typing import List
from enum import Enum

from .core import Deck, Card


class PokerHand():

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


class PokerPhase(Enum):
    PREFLOP = "Preflop"
    FLOP = "Flop"
    TURN = "Turn"
    RIVER = "River"


class PokerDealer():

    def __init__(self, deck: Deck) -> None:
        self.deck = deck
        self.deck.shuffle()
        self.next_phase = PokerPhase.PREFLOP

    def reset(self) -> None:
        self.deck.reset()
        self.deck.shuffle()
        self.next_phase = PokerPhase.PREFLOP

    def deal_preflop(self, num_players: int) -> List[PokerHand]:
        if self.next_phase != PokerPhase.PREFLOP:
            raise ValueError("Cannot deal preflop in current phase")

        if num_players > 9 or num_players < 2:
            raise ValueError("Number of players must be between 2 and 9")
        
        fst_pass_cards = [self.deck.draw_one() for _ in range(num_players)]
        snd_pass_cards = [self.deck.draw_one() for _ in range(num_players)]
        hands = zip(fst_pass_cards, snd_pass_cards)

        self.next_phase = PokerPhase.FLOP
        return [PokerHand(cards[0], cards[1]) for cards in hands]
    
    def deal_flop(self) -> List[Card]:
        if self.next_phase != PokerPhase.FLOP:
            raise ValueError("Cannot deal flop in current phase")
        
        self.deck.draw_one()

        self.next_phase = PokerPhase.TURN
        return self.deck.draw(3)
    
    def deal_turn(self) -> Card:
        if self.next_phase != PokerPhase.TURN:
            raise ValueError("Cannot deal turn in current phase")
        
        self.deck.draw_one()

        self.next_phase = PokerPhase.RIVER
        return self.deck.draw_one()
    
    def deal_river(self) -> Card:
        if self.next_phase != PokerPhase.RIVER:
            raise ValueError("Cannot deal river in current phase")
        
        self.deck.draw_one()

        self.next_phase = None
        return self.deck.draw_one()
