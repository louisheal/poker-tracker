import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from parser import parse_histories

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

base = os.path.dirname(__file__)
histories_dir = os.path.normpath(os.path.join(base, '..', 'hand_histories'))

paths = []
if os.path.isdir(histories_dir):
    for filename in os.listdir(histories_dir):
        path = os.path.join(histories_dir, filename)
        if not os.path.isfile(path):
            continue
        paths.append(path)

ranges = parse_histories(paths)

@app.get("/")
def get_ranges():
    return ranges.json()
