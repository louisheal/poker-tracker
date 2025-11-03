from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random

class Card():
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def to_json(self):
        return {
            "Rank": self.rank,
            "Suit": self.suit
        }

class Hand():
    def __init__(self, fst_card: Card, snd_card: Card):
        self.fst_card = fst_card
        self.snd_card = snd_card

    def to_json(self):
        return {
            "FstCard": self.fst_card.to_json(),
            "SndCard": self.snd_card.to_json()
        }

ranks = ['2','3','4','5','6','7','8','9','T','J','Q','K','A']
suits = ['Hearts','Diamonds','Spades','Clubs']

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

@app.get("/hand")
def get_hand():
    cards = []
    for _ in range(2):
        rank = random.sample(ranks, 1)[0]
        suit = random.sample(suits, 1)[0]
        cards.append(Card(rank, suit))
    return Hand(cards[0], cards[1]).to_json()
