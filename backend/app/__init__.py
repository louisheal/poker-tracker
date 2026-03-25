import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.loader import load_hand_histories
from app.routers import ranges, flop, turn, river, volume, line_analysis, hand_types

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5174"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = load_hand_histories()
    app.state.store = store

    app.include_router(ranges.router)
    app.include_router(flop.router, prefix="/flop")
    app.include_router(turn.router, prefix="/turn")
    app.include_router(river.router, prefix="/river")
    app.include_router(volume.router, prefix="/hands/volume")
    app.include_router(hand_types.router, prefix="/line-analysis/hand-types")
    app.include_router(line_analysis.router, prefix="/line-analysis")

    return app