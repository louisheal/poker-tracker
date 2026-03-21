import logging

from mcp.server.fastmcp import FastMCP

from app.loader import load_hand_histories
from app.models import (
	FlopFilter, Flops, ActionSequence, Runout, FlopRankTexture,
	RiverFilter, Rivers,
	TurnFilter, Turns, Ranges,
	BoardType, PotType,
)
from app.routers.params import (
	BOARD_TYPE_MAP, POT_TYPE_MAP, RUNOUT_MAP,
	ACTION_SEQUENCE_MAP, FLOP_RANK_MAP,
	in_date_range, parse_optional_date,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("Poker Tracker")

store = load_hand_histories()


def _parse_date(value: str | None):
	if not value:
		return None
	return parse_optional_date(value)


def _resolve(values, mapping, enum_cls):
	if not values:
		return list(enum_cls)
	resolved = [mapping[v.upper()] for v in values if v.upper() in mapping]
	return resolved if resolved else list(enum_cls)


def _resolve_bool(values):
	if values is None or len(values) == 0:
		return [True, False]
	return values


@mcp.tool()
def get_cbet_stats(
	hero_in_position: list[bool] | None = None,
	hero_preflop_raiser: list[bool] | None = None,
	board_types: list[str] | None = None,
	pot_types: list[str] | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	bet_size_min: float | None = None,
	bet_size_max: float | None = None,
) -> dict:
	"""Get flop continuation bet statistics.

	Filter by position (IP/OOP), whether hero was the preflop raiser,
	board texture (MONOTONE, TWO_TONE, RAINBOW), and pot type (SRP, THREE_BET, FOUR_BET).

	bet_size_min/bet_size_max filter by bet size as % of pot (0-200).
	Only hands where a bet was made (cbet or donk) are filtered; check-check hands pass through.

	Returns cbet%, fold-to-cbet%, raise-to-cbet%, donk-bet%, fold-to-donk%, raise-to-donk%, and hand count.
	"""
	start = _parse_date(start_date)
	end = _parse_date(end_date)
	f = FlopFilter(
		hero_in_position=_resolve_bool(hero_in_position),
		hero_preflop_raiser=_resolve_bool(hero_preflop_raiser),
		board_types=_resolve(board_types, BOARD_TYPE_MAP, BoardType),
		pot_types=_resolve(pot_types, POT_TYPE_MAP, PotType),
		bet_size_min=bet_size_min,
		bet_size_max=bet_size_max,
	)
	filtered = [e for e in store.cbet_events if in_date_range(e.played_on, start, end)]
	cbets = Flops()
	for e in filtered:
		cbets.add_event(e)
	return cbets.json(f)


@mcp.tool()
def get_turn_stats(
	hero_in_position: list[bool] | None = None,
	hero_preflop_raiser: list[bool] | None = None,
	board_types: list[str] | None = None,
	pot_types: list[str] | None = None,
	turn_runouts: list[str] | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
) -> dict:
	"""Get turn action statistics broken down by flop action line (XX, XBC, XBRC, BC).

	Filter by position, PFR status, board texture, pot type, and turn card type
	(OVERCARD, FLUSH_COMPLETING, PAIRED, OTHER).

	Returns per flop action line: hero bet%, villain fold/raise to hero bet,
	villain bet%, hero fold/raise to villain bet, and hand count.
	"""
	start = _parse_date(start_date)
	end = _parse_date(end_date)
	f = TurnFilter(
		hero_in_position=_resolve_bool(hero_in_position),
		hero_preflop_raiser=_resolve_bool(hero_preflop_raiser),
		board_types=_resolve(board_types, BOARD_TYPE_MAP, BoardType),
		pot_types=_resolve(pot_types, POT_TYPE_MAP, PotType),
		turn_runouts=_resolve(turn_runouts, RUNOUT_MAP, Runout),
	)
	filtered = [e for e in store.turn_events if in_date_range(e.played_on, start, end)]
	turns = Turns()
	for e in filtered:
		turns.add_event(e)
	return turns.json(f)


@mcp.tool()
def get_river_stats(
	hero_in_position: list[bool] | None = None,
	board_types: list[str] | None = None,
	pot_types: list[str] | None = None,
	flop_actions: list[str] | None = None,
	flop_rank_textures: list[str] | None = None,
	turn_runouts: list[str] | None = None,
	turn_action_sequences: list[str] | None = None,
	river_runouts: list[str] | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
) -> dict:
	"""Get river action, showdown, and average pot statistics.

	Extensive filtering: position, board texture (MONOTONE/TWO_TONE/RAINBOW),
	pot type (SRP/THREE_BET/FOUR_BET), flop actions (XX/XBC/XBRC/BC),
	flop rank texture (TRIPS/PAIRED/UNPAIRED), turn card type (OVERCARD/FLUSH_COMPLETING/PAIRED/OTHER),
	turn actions (XX/XBC/XBRC/BC), river card type (OVERCARD/FLUSH_COMPLETING/PAIRED/OTHER).

	Returns:
	- actions: hero/villain bet/fold/raise percentages and hand count
	- showdown: BB won/lost per hand by river action line (XX/XBC/XBRC/BC)
	- avg_pot: average pot size in BB by river action line
	"""
	start = _parse_date(start_date)
	end = _parse_date(end_date)
	f = RiverFilter(
		hero_in_position=_resolve_bool(hero_in_position),
		board_types=_resolve(board_types, BOARD_TYPE_MAP, BoardType),
		pot_types=_resolve(pot_types, POT_TYPE_MAP, PotType),
		flop_actions=_resolve(flop_actions, ACTION_SEQUENCE_MAP, ActionSequence),
		flop_rank_textures=_resolve(flop_rank_textures, FLOP_RANK_MAP, FlopRankTexture),
		turn_runouts=_resolve(turn_runouts, RUNOUT_MAP, Runout),
		turn_action_sequences=_resolve(turn_action_sequences, ACTION_SEQUENCE_MAP, ActionSequence),
		river_runouts=_resolve(river_runouts, RUNOUT_MAP, Runout),
	)
	filtered = [e for e in store.river_events if in_date_range(e.played_on, start, end)]
	rivers = Rivers()
	for e in filtered:
		rivers.add_event(e)
	return rivers.json(f)


@mcp.tool()
def get_preflop_ranges(
	start_date: str | None = None,
	end_date: str | None = None,
) -> dict:
	"""Get preflop hand ranges showing fold/raise/call counts per hand combo.

	Returns data grouped by pot type (SRP, THREE_BET, FOUR_BET) and position
	(LJ, HJ, CO, BTN, SB, BB). Each hand combo (e.g. AKs, QQ, T9o) shows
	the number of folds, raises, and calls.
	"""
	start = _parse_date(start_date)
	end = _parse_date(end_date)
	filtered = [e for e in store.range_events if in_date_range(e.played_on, start, end)]
	ranges = Ranges()
	for e in filtered:
		ranges.add_hand(e.hand_key, e.position, e.action, e.pot_type, e.villain)
	return ranges.json()


@mcp.tool()
def find_leaks(
	start_date: str | None = None,
	end_date: str | None = None,
	min_hands: int = 30,
) -> list[dict]:
	"""Automatically scan for poker leaks by comparing stats across spots.

	Checks cbet frequencies IP vs OOP, turn/river bet frequencies by board texture
	and runout type, fold-to-bet frequencies, and showdown profitability.
	Only reports spots with at least min_hands sample size.

	Returns a list of identified leaks, each with:
	- spot: description of the scenario
	- stat: the metric name
	- value: the observed value
	- concern: why this might be a leak
	- hand_count: sample size
	"""
	start = _parse_date(start_date)
	end = _parse_date(end_date)
	leaks: list[dict] = []

	for ip_label, ip_val in [("IP", [True]), ("OOP", [False])]:
		f = CBetFilter(
			hero_in_position=ip_val,
			hero_preflop_raiser=[True],
			board_types=list(BoardType),
			pot_types=list(PotType),
		)
		filtered = [e for e in store.cbet_events if in_date_range(e.played_on, start, end)]
		cbets = CBets()
		for e in filtered:
			cbets.add_event(e)
		stats = cbets.json(f)
		if stats["hand_count"] >= min_hands:
			cbet_pct = stats["cbet_pct"]
			if cbet_pct > 75:
				leaks.append({"spot": f"Flop cbet as PFR {ip_label}", "stat": "cbet_pct", "value": round(cbet_pct, 1), "concern": "Cbetting too frequently — opponents can exploit by check-raising more", "hand_count": stats["hand_count"]})
			elif cbet_pct < 25:
				leaks.append({"spot": f"Flop cbet as PFR {ip_label}", "stat": "cbet_pct", "value": round(cbet_pct, 1), "concern": "Cbetting too infrequently — missing value and allowing free cards", "hand_count": stats["hand_count"]})
			fcbet = stats["fcbet_pct"]
			if fcbet > 60:
				leaks.append({"spot": f"Villain fold to cbet {ip_label}", "stat": "fcbet_pct", "value": round(fcbet, 1), "concern": "Villain overfolds to cbet — increase cbet bluff frequency", "hand_count": stats["hand_count"]})

	for ip_label, ip_val in [("IP", [True]), ("OOP", [False])]:
		f = RiverFilter(hero_in_position=ip_val)
		filtered = [e for e in store.river_events if in_date_range(e.played_on, start, end)]
		rivers = Rivers()
		for e in filtered:
			rivers.add_event(e)
		stats = rivers.json(f)
		actions = stats["actions"]
		if actions["hand_count"] >= min_hands:
			hero_fold = actions["hero_fold_to_villain_bet_pct"]
			if hero_fold > 60:
				leaks.append({"spot": f"River facing bet {ip_label}", "stat": "hero_fold_to_villain_bet_pct", "value": round(hero_fold, 1), "concern": "Folding too often to river bets — opponent can bluff profitably", "hand_count": actions["hand_count"]})
			villain_fold = actions["villain_fold_to_hero_bet_pct"]
			if villain_fold > 55:
				leaks.append({"spot": f"River hero bets {ip_label}", "stat": "villain_fold_to_hero_bet_pct", "value": round(villain_fold, 1), "concern": "Villain overfolds river — increase bluff frequency on river", "hand_count": actions["hand_count"]})

		for seq in ActionSequence:
			sd = stats["showdown"].get(seq.value, {})
			if sd.get("hand_count", 0) >= min_hands:
				bb = sd["bb_per_hand"]
				if bb < -3:
					leaks.append({"spot": f"Showdown {seq.value} {ip_label}", "stat": "bb_per_hand", "value": bb, "concern": f"Losing badly at showdown in {seq.value} line — review hand selection", "hand_count": sd["hand_count"]})

	for runout in Runout:
		f = TurnFilter(turn_runouts=[runout])
		filtered = [e for e in store.turn_events if in_date_range(e.played_on, start, end)]
		turns = Turns()
		for e in filtered:
			turns.add_event(e)
		stats = turns.json(f)
		for seq_key, seq_stats in stats.items():
			if seq_stats["hand_count"] >= min_hands:
				hero_bet = seq_stats["hero_bet_pct"]
				if hero_bet > 80:
					leaks.append({"spot": f"Turn bet {seq_key} on {runout.value}", "stat": "hero_bet_pct", "value": round(hero_bet, 1), "concern": "Betting too frequently — vulnerable to check-raises", "hand_count": seq_stats["hand_count"]})
				villain_fold = seq_stats["villain_fold_to_hero_bet_pct"]
				if villain_fold > 55 and seq_stats["hand_count"] >= min_hands:
					leaks.append({"spot": f"Turn bet {seq_key} on {runout.value}", "stat": "villain_fold_to_hero_bet_pct", "value": round(villain_fold, 1), "concern": "Villain overfolds turn — barrel more aggressively", "hand_count": seq_stats["hand_count"]})

	return leaks


@mcp.tool()
def compare_lines(
	line_a_hero_ip: list[bool] | None = None,
	line_a_board_types: list[str] | None = None,
	line_a_pot_types: list[str] | None = None,
	line_a_flop_actions: list[str] | None = None,
	line_a_turn_runouts: list[str] | None = None,
	line_a_river_runouts: list[str] | None = None,
	line_b_hero_ip: list[bool] | None = None,
	line_b_board_types: list[str] | None = None,
	line_b_pot_types: list[str] | None = None,
	line_b_flop_actions: list[str] | None = None,
	line_b_turn_runouts: list[str] | None = None,
	line_b_river_runouts: list[str] | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
) -> dict:
	"""Compare river stats between two different filter configurations (Line A vs Line B).

	Useful for questions like: "Am I more profitable betting IP or OOP?",
	"Is my winrate better on rainbow vs two-tone boards?",
	"Should I take the XBC or BC line?"

	Returns side-by-side river action stats, showdown results, and average pot sizes for each line.
	"""
	start = _parse_date(start_date)
	end = _parse_date(end_date)
	filtered = [e for e in store.river_events if in_date_range(e.played_on, start, end)]

	def _build_and_query(hero_ip, board_types, pot_types, flop_actions, turn_runouts, river_runouts):
		f = RiverFilter(
			hero_in_position=_resolve_bool(hero_ip),
			board_types=_resolve(board_types, BOARD_TYPE_MAP, BoardType),
			pot_types=_resolve(pot_types, POT_TYPE_MAP, PotType),
			flop_actions=_resolve(flop_actions, ACTION_SEQUENCE_MAP, ActionSequence),
			turn_runouts=_resolve(turn_runouts, RUNOUT_MAP, Runout),
			river_runouts=_resolve(river_runouts, RUNOUT_MAP, Runout),
		)
		rivers = Rivers()
		for e in filtered:
			rivers.add_event(e)
		return rivers.json(f)

	return {
		"line_a": _build_and_query(line_a_hero_ip, line_a_board_types, line_a_pot_types, line_a_flop_actions, line_a_turn_runouts, line_a_river_runouts),
		"line_b": _build_and_query(line_b_hero_ip, line_b_board_types, line_b_pot_types, line_b_flop_actions, line_b_turn_runouts, line_b_river_runouts),
	}


if __name__ == "__main__":
	mcp.run(transport="stdio")
