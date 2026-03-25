from app.models.enums import MadeHandType, FlushDrawType, StraightDrawType
from typing import Tuple, Dict


HandTriple = Tuple[MadeHandType, FlushDrawType, StraightDrawType]


def is_impossible_triple(made: MadeHandType, fd: FlushDrawType, sd: StraightDrawType) -> bool:
    if made == MadeHandType.FLUSH and fd != FlushDrawType.NONE:
        return True
    if made == MadeHandType.STRAIGHT and sd != StraightDrawType.NONE:
        return True
    if made in (MadeHandType.STRAIGHT_FLUSH, MadeHandType.QUADS, MadeHandType.FULL_HOUSE):
        return fd != FlushDrawType.NONE or sd != StraightDrawType.NONE
    return False


FLUSH_DRAW_COMPLETION = {
    "flop": {
        FlushDrawType.FRONT_DOOR: 0.35,
        FlushDrawType.BACK_DOOR: 0.04,
        FlushDrawType.NONE: 0.0,
    },
    "turn": {
        FlushDrawType.FRONT_DOOR: 0.196,
        FlushDrawType.BACK_DOOR: 0.0,
        FlushDrawType.NONE: 0.0,
    },
    "river": {
        FlushDrawType.FRONT_DOOR: 0.0,
        FlushDrawType.BACK_DOOR: 0.0,
        FlushDrawType.NONE: 0.0,
    },
}


STRAIGHT_DRAW_COMPLETION = {
    "flop": {
        StraightDrawType.OESD: 0.32,
        StraightDrawType.GUTSHOT: 0.17,
        StraightDrawType.NONE: 0.0,
    },
    "turn": {
        StraightDrawType.OESD: 0.174,
        StraightDrawType.GUTSHOT: 0.087,
        StraightDrawType.NONE: 0.0,
    },
    "river": {
        StraightDrawType.OESD: 0.0,
        StraightDrawType.GUTSHOT: 0.0,
        StraightDrawType.NONE: 0.0,
    },
}


MADE_HAND_RANK = {
    MadeHandType.STRAIGHT_FLUSH: 11,
    MadeHandType.QUADS: 10,
    MadeHandType.FULL_HOUSE: 9,
    MadeHandType.FLUSH: 8,
    MadeHandType.STRAIGHT: 7,
    MadeHandType.SET: 6,
    MadeHandType.TWO_PAIR: 5,
    MadeHandType.OVERPAIR: 4,
    MadeHandType.TOP_PAIR: 3,
    MadeHandType.PAIR: 2,
    MadeHandType.ACE_HIGH: 1,
    MadeHandType.NO_MADE_HAND: 0,
}


def made_vs_made(hero: MadeHandType, villain: MadeHandType) -> float:
    h, v = MADE_HAND_RANK[hero], MADE_HAND_RANK[villain]
    if h > v: return 0.92
    if h < v: return 0.08
    return 0.50


def _best_made(current_made: MadeHandType, flush_hit: bool, straight_hit: bool) -> MadeHandType:
    best = current_made
    if flush_hit and MADE_HAND_RANK[MadeHandType.FLUSH] > MADE_HAND_RANK[best]:
        best = MadeHandType.FLUSH
    if straight_hit and MADE_HAND_RANK[MadeHandType.STRAIGHT] > MADE_HAND_RANK[best]:
        best = MadeHandType.STRAIGHT
    return best


def _calculate_triple_equity(
    hero_made: MadeHandType, hero_fd: FlushDrawType, hero_sd: StraightDrawType,
    villain_made: MadeHandType, villain_fd: FlushDrawType, villain_sd: StraightDrawType,
    street: str,
) -> float:
    h_flush_hit = FLUSH_DRAW_COMPLETION[street][hero_fd]
    h_straight_hit = STRAIGHT_DRAW_COMPLETION[street][hero_sd]
    v_flush_hit = FLUSH_DRAW_COMPLETION[street][villain_fd]
    v_straight_hit = STRAIGHT_DRAW_COMPLETION[street][villain_sd]
    equity = 0.0
    for h_fh, h_fp in [(True, h_flush_hit), (False, 1 - h_flush_hit)]:
        for h_sh, h_sp in [(True, h_straight_hit), (False, 1 - h_straight_hit)]:
            for v_fh, v_fp in [(True, v_flush_hit), (False, 1 - v_flush_hit)]:
                for v_sh, v_sp in [(True, v_straight_hit), (False, 1 - v_straight_hit)]:
                    p = h_fp * h_sp * v_fp * v_sp
                    if p < 0.001:
                        continue
                    h_effective = _best_made(hero_made, h_fh, h_sh)
                    v_effective = _best_made(villain_made, v_fh, v_sh)
                    equity += p * made_vs_made(h_effective, v_effective)
    return equity


def _build_valid_triples() -> list[HandTriple]:
    return [
        (made, fd, sd)
        for made in MadeHandType
        for fd in FlushDrawType
        for sd in StraightDrawType
        if not is_impossible_triple(made, fd, sd)
    ]


def _build_equity_grid() -> Dict[str, Dict[Tuple[HandTriple, HandTriple], float]]:
    grid = {}
    valid_triples = _build_valid_triples()
    for street in ("flop", "turn", "river"):
        street_grid = {}
        for hero in valid_triples:
            for villain in valid_triples:
                street_grid[(hero, villain)] = _calculate_triple_equity(
                    hero[0], hero[1], hero[2],
                    villain[0], villain[1], villain[2],
                    street,
                )
        grid[street] = street_grid
    return grid


def get_equity(hero: HandTriple, villain: HandTriple, street: str) -> float:
    """O(1) equity lookup from precomputed grid."""
    return _build_equity_grid()[street][(hero, villain)]
