from fastapi import APIRouter, Depends, Query

from app.dependencies import get_store, get_date_range
from app.loader import EventStore
from app.models import LineFilter
from app.routers.params import parse_board_type_list, parse_pot_type_list, parse_runout_list
from app.routers.line_analysis import _split_action_prefix
from app.parsers.ev_calculator import calculate_ev_open, calculate_ev_vs_bet

router = APIRouter()

DEFAULT_BET_SIZES = [33, 66, 133, 200]


@router.get("")
def get_hand_ev(
	hero_in_position: bool | None = Query(default=None),
	hero_preflop_raiser: bool | None = Query(default=None),
	board_types: list[str] | None = Query(default=None),
	pot_types: list[str] | None = Query(default=None),
	turn_runouts: list[str] | None = Query(default=None),
	river_runouts: list[str] | None = Query(default=None),
	actions: list[str] | None = Query(default=None),
	include_pool: bool = Query(default=False),
	bet_sizes: list[int] | None = Query(default=None),
	store: EventStore = Depends(get_store),
	dates: tuple = Depends(get_date_range),
):
	start, end = dates
	f = LineFilter(
		hero_in_position=hero_in_position,
		hero_preflop_raiser=hero_preflop_raiser,
		pot_types=parse_pot_type_list(pot_types),
		board_types=parse_board_type_list(board_types),
		turn_runouts=parse_runout_list(turn_runouts) if turn_runouts else None,
		river_runouts=parse_runout_list(river_runouts) if river_runouts else None,
		include_pool=include_pool,
	)

	flop_actions, turn_actions, river_actions = _split_action_prefix(actions)
	node_data = store.line_events.ev_node_data(f, flop_actions, turn_actions, river_actions, start=start, end=end)

	total = node_data["fold_count"] + node_data["call_count"] + node_data["raise_count"]
	sizes = bet_sizes or DEFAULT_BET_SIZES

	if node_data["hero_faces_bet"] and node_data["villain_bet_bb"] is not None:
		ev_result = calculate_ev_vs_bet(node_data, node_data["villain_bet_bb"])
	else:
		ev_result = calculate_ev_open(node_data, sizes)

	fold_pct = (node_data["fold_count"] / total * 100) if total else 0
	call_pct = (node_data["call_count"] / total * 100) if total else 0
	raise_pct = (node_data["raise_count"] / total * 100) if total else 0

	return {
		**ev_result,
		"villain_data": {
			"range_count": total,
			"fold_pct": round(fold_pct, 1),
			"call_pct": round(call_pct, 1),
			"raise_pct": round(raise_pct, 1),
		},
		"pot_bb": node_data["pot_bb"],
		"street": node_data["street"],
		"hand_count": node_data["hand_count"],
		"next_actor": node_data["next_actor"],
	}
