import uuid

from playing_cards_lib import Deck
from playing_cards_lib.poker import PokerDealer

from dto import HandDto
from fastapi import HTTPException, status

hand_store = {}

def deal_hand():
    dealer = PokerDealer(Deck())
    hand = dealer.deal_preflop(num_players=6)[0]
    corr_id = str(uuid.uuid4())
    hand_store[corr_id] = hand
    return HandDto(corr_id, hand)

def fold_hand(id: str):
    hand = hand_store.pop(id, None)
    if not hand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hand not found")

def raise_hand(id: str):
    hand = hand_store.pop(id, None)
    if not hand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hand not found")