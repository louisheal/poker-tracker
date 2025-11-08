from typing import List
from enum import Enum

from .core import Deck, Card


class PokerHand():

    def __init__(self, fst_card: Card, snd_card: Card):
        """
        Initialize a PokerHand with two cards.
        Args:
            fst_card (Card): The first card dealt to the player.
            snd_card (Card): The second card dealt to the player.
        """
        if fst_card < snd_card:
            fst_card, snd_card = snd_card, fst_card

        self.fst_card = fst_card
        self.snd_card = snd_card

    def to_json(self):
        """
        Serialize the PokerHand to a JSON-compatible dictionary.
        Returns:
            dict: Dictionary with keys 'FstCard' and 'SndCard'.
        """
        return {
            "FstCard": self.fst_card.to_json(),
            "SndCard": self.snd_card.to_json()
        }


class PokerPhase(Enum):
    """
    Enum representing the phases of a Texas Hold'em poker hand.
    """
    PREFLOP = "Preflop"
    FLOP = "Flop"
    TURN = "Turn"
    RIVER = "River"


class PokerDealer():
    """
    Manages the dealing of cards and game phases for Texas Hold'em poker.
    Tracks the deck and current phase, and provides methods to deal cards for each street.

    Example usage:

        from core import Deck
        from poker import PokerDealer

        deck = Deck()
        dealer = PokerDealer(deck)
        dealer.reset()
        hands = dealer.deal_preflop(num_players=6)
        flop = dealer.deal_flop()
        turn = dealer.deal_turn()
        river = dealer.deal_river()

    Raises:
        ValueError: If dealing methods are called out of order or with invalid arguments.
    """

    def __init__(self, deck: Deck) -> None:
        """
        Initialize the PokerDealer with a deck and set the phase to preflop.
        Args:
            deck (Deck): The deck to use for dealing cards.
        """
        self.deck = deck
        self.deck.shuffle()
        self.next_phase = PokerPhase.PREFLOP

    def reset(self) -> None:
        """
        Reset the deck and shuffle, starting a new hand at the preflop phase.
        """
        self.deck.reset()
        self.deck.shuffle()
        self.next_phase = PokerPhase.PREFLOP

    def deal_preflop(self, num_players: int) -> List[PokerHand]:
        """
        Deal two cards to each player for the preflop phase.
        Args:
            num_players (int): Number of players (2-9).
        Returns:
            List[PokerHand]: List of PokerHand objects for each player.
        Raises:
            ValueError: If not in preflop phase or invalid player count.
        """
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
        """
        Deal the flop (three community cards) after burning one card.
        Returns:
            List[Card]: List of three community cards.
        Raises:
            ValueError: If not in flop phase.
        """
        if self.next_phase != PokerPhase.FLOP:
            raise ValueError("Cannot deal flop in current phase")
        
        self.deck.draw_one()

        self.next_phase = PokerPhase.TURN
        return self.deck.draw(3)
    
    def deal_turn(self) -> Card:
        """
        Deal the turn (one community card) after burning one card.
        Returns:
            Card: The turn card.
        Raises:
            ValueError: If not in turn phase.
        """
        if self.next_phase != PokerPhase.TURN:
            raise ValueError("Cannot deal turn in current phase")
        
        self.deck.draw_one()

        self.next_phase = PokerPhase.RIVER
        return self.deck.draw_one()
    
    def deal_river(self) -> Card:
        """
        Deal the river (one community card) after burning one card.
        Returns:
            Card: The river card.
        Raises:
            ValueError: If not in river phase.
        """
        if self.next_phase != PokerPhase.RIVER:
            raise ValueError("Cannot deal river in current phase")
        
        self.deck.draw_one()

        self.next_phase = None
        return self.deck.draw_one()
