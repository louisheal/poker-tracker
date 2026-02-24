import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rush_and_cash_parser import POSITIONS, Parser, Range

app = FastAPI()

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def get_ranges():
    ranges: dict[str, Range] = {}
    for position in POSITIONS:
        ranges[position] = Range()
        
    parser = Parser(ranges)

    base = os.path.dirname(__file__)
    histories_dir = os.path.normpath(os.path.join(base, '..', 'hand_histories'))

    if os.path.isdir(histories_dir):
        for filename in os.listdir(histories_dir):
            sample = os.path.join(histories_dir, filename)
            if not os.path.isfile(sample):
                continue
            with open(sample, 'r', encoding='utf-8') as f:
                for line in f:
                    parser.next(line)
            
    return ranges
