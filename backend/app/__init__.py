import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.loader import load_hand_histories
from app.routers import ranges, flop, turn, river, volume, line_analysis, hand_types, hand_ev, stats, solver

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SOLVER_CHECKPOINT = os.path.join(os.path.dirname(__file__), "..", "solver", "checkpoints", "best.pt")


def _load_solver_model():
    """Load the trained solver model if a checkpoint exists."""
    if not os.path.isfile(SOLVER_CHECKPOINT):
        logger.info("No solver checkpoint found, using mock solver")
        return None

    try:
        import torch
        from solver.model import SolverTransformer

        model = SolverTransformer()
        checkpoint = torch.load(SOLVER_CHECKPOINT, map_location="cpu", weights_only=True)
        model.load_state_dict(checkpoint)
        model.eval()
        logger.info("Solver model loaded from checkpoint")
        return model
    except Exception as e:
        logger.warning(f"Failed to load solver model: {e}")
        return None


def create_app() -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5174"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    db_path = load_hand_histories()
    app.state.db_path = db_path

    # Load solver model (None = use mock)
    app.state.solver_model = _load_solver_model()

    app.include_router(ranges.router)
    app.include_router(flop.router, prefix="/flop")
    app.include_router(turn.router, prefix="/turn")
    app.include_router(river.router, prefix="/river")
    app.include_router(volume.router, prefix="/hands/volume")
    app.include_router(hand_types.router, prefix="/line-analysis/hand-types")
    app.include_router(hand_ev.router, prefix="/line-analysis/hand-ev")
    app.include_router(line_analysis.router, prefix="/line-analysis")
    app.include_router(stats.router, prefix="/stats")
    app.include_router(solver.router, prefix="/solver")

    return app