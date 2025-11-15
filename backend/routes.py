from fastapi import APIRouter, HTTPException, Response, status

from services import deal_hand, fold_hand, raise_hand

router = APIRouter()

@router.get("/hand")
def get_hand_controller():
    dto = deal_hand()
    return dto.to_json()

@router.post("/hand/{id}/fold")
def fold_hand_controller(id: str):
    fold_hand(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/hand/{id}/raise")
def raise_hand_controller(id: str):
    raise_hand(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
