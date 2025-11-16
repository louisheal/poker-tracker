from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from playing_cards_lib import Deck
from playing_cards_lib.poker import PokerDealer

from services import GtoRanges, PokerService, HandTracker

router = APIRouter()
poker_service = PokerService(PokerDealer(Deck()), HandTracker(), GtoRanges())

class PositionRequest(BaseModel):
    pos: int

class RangeRequest(BaseModel):
    pos: int

@router.get("/hand")
def get_hand_controller():
    dto = poker_service.deal_hand()
    return dto.to_json()

@router.post("/hand/{id}/fold")
def fold_hand_controller(id: str, req: PositionRequest):
    poker_service.fold_hand(id, req.pos)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/hand/{id}/raise")
def raise_hand_controller(id: str, req: PositionRequest):
    poker_service.raise_hand(id, req.pos)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/range")
def get_range_controller(req: RangeRequest):
    return poker_service.get_ranges(req.pos)