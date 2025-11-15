from playing_cards_lib.poker import PokerHand


class HandDto:

    def __init__(self, id: str, hand: PokerHand):
        self.id = id
        self.hand = hand

    def to_json(self):
        data = self.hand.to_json()
        data["Id"] = self.id
        return data
