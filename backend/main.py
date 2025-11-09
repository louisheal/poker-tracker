from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from playing_cards_lib import Deck
from playing_cards_lib.poker import PokerDealer

app = FastAPI()

origins = [
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# need to create a service layer - this should be the controller layer only
# 

@app.get("/hand")
def get_hand():
    dealer = PokerDealer(Deck())
    hands = dealer.deal_preflop(num_players=6)
    return hands[0].to_json()

@app.post("/fold")
def fold_hand():
    dealer = PokerDealer(Deck())
    hands = dealer.deal_preflop(num_players=6)
    return hands[0].to_json()

@app.post("/raise")
def fold_hand():
    dealer = PokerDealer(Deck())
    hands = dealer.deal_preflop(num_players=6)
    return hands[0].to_json()