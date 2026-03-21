import logging

from app.models.events import CBetEvent, TurnEvent, RiverEvent, LineEvent

from .common import RIVER_RE
from .board import parse_board_type, parse_turn_runout, parse_river_runout, parse_flop_rank_texture
from .preflop import (
	parse_hero_sees_flop, parse_preflop_pot_type, parse_hero_in_position,
	parse_pot_at_flop, parse_hero_pnl, parse_hero_preflop_raiser,
)
from .flop import parse_flop_cbet, parse_flop_actions_detailed, parse_flop_action_sequence, _parse_fold_to_raise
from .turn import parse_turn_actions, parse_turn_action_sequence
from .river import parse_river_actions, parse_river_action_sequence, parse_river_showdown_type, parse_showdown_result

logger = logging.getLogger(__name__)


def parse_cbet_event(lines: list[str]) -> CBetEvent | None:
	board_type = parse_board_type(lines)
	if board_type is None:
		return None
	if not parse_hero_sees_flop(lines):
		return None
	event = CBetEvent()
	event.pot_type = parse_preflop_pot_type(lines)
	event.board_type = board_type
	event.hero_preflop_raiser = parse_hero_preflop_raiser(lines)
	event.hero_in_position = parse_hero_in_position(lines)
	cbet, fold_to_cbet, raise_to_cbet, donk_bet, fold_to_donk_bet, raise_to_donk_bet, cbet_amount, donk_bet_amount = parse_flop_cbet(lines, event.hero_preflop_raiser)
	event.cbet = cbet
	event.fold_to_cbet = fold_to_cbet
	event.raise_to_cbet = raise_to_cbet
	event.donk_bet = donk_bet
	event.fold_to_donk_bet = fold_to_donk_bet
	event.raise_to_donk_bet = raise_to_donk_bet

	# Compute pot-relative bet sizes
	pot_at_flop = parse_pot_at_flop(lines)
	if pot_at_flop and pot_at_flop > 0:
		pot_dollars = pot_at_flop * 0.02
		if cbet_amount is not None:
			event.cbet_size_pct = (cbet_amount / pot_dollars) * 100
		if donk_bet_amount is not None:
			event.donk_bet_size_pct = (donk_bet_amount / pot_dollars) * 100

	return event


def parse_turn_event(lines: list[str]) -> TurnEvent | None:
	board_type = parse_board_type(lines)
	if board_type is None:
		return None
	if not parse_hero_sees_flop(lines):
		return None
	
	flop_action_sequence = parse_flop_action_sequence(lines, parse_hero_preflop_raiser(lines))
	if flop_action_sequence is None:
		return None
	
	turn_runout = parse_turn_runout(lines)
	if turn_runout is None:
		return None
	
	hero_bet_turn, villain_fold_to_hero_bet, villain_raise_to_hero_bet, villain_bet_turn, hero_fold_to_villain_bet, hero_raise_to_villain_bet = parse_turn_actions(lines)
	
	event = TurnEvent()
	event.pot_type = parse_preflop_pot_type(lines)
	event.board_type = board_type
	event.hero_preflop_raiser = parse_hero_preflop_raiser(lines)
	event.hero_in_position = parse_hero_in_position(lines)
	event.flop_action_sequence = flop_action_sequence
	event.turn_runout = turn_runout
	event.hero_bet_turn = hero_bet_turn
	event.villain_fold_to_hero_bet = villain_fold_to_hero_bet
	event.villain_raise_to_hero_bet = villain_raise_to_hero_bet
	event.villain_bet_turn = villain_bet_turn
	event.hero_fold_to_villain_bet = hero_fold_to_villain_bet
	event.hero_raise_to_villain_bet = hero_raise_to_villain_bet
	return event


def parse_river_event(lines: list[str]) -> RiverEvent | None:
	board_type = parse_board_type(lines)
	if board_type is None:
		return None
	if not parse_hero_sees_flop(lines):
		return None

	has_river = any(RIVER_RE.search(line) for line in lines)
	if not has_river:
		return None

	flop_action_sequence = parse_flop_action_sequence(lines, parse_hero_preflop_raiser(lines))
	if flop_action_sequence is None:
		return None

	flop_rank_texture = parse_flop_rank_texture(lines)
	if flop_rank_texture is None:
		return None

	turn_runout = parse_turn_runout(lines)
	if turn_runout is None:
		return None

	turn_action_sequence = parse_turn_action_sequence(lines)
	if turn_action_sequence is None:
		return None

	river_runout = parse_river_runout(lines)
	if river_runout is None:
		return None

	river_action_sequence = parse_river_action_sequence(lines)
	if river_action_sequence is None:
		return None

	hero_bet, v_fold, v_raise, v_bet, h_fold, h_raise = parse_river_actions(lines)
	went_to_showdown, hero_won, pot_size_bb = parse_showdown_result(lines)
	showdown_type = parse_river_showdown_type(lines) if went_to_showdown else None

	event = RiverEvent()
	event.pot_type = parse_preflop_pot_type(lines)
	event.board_type = board_type
	event.hero_in_position = parse_hero_in_position(lines)
	event.flop_action_sequence = flop_action_sequence
	event.flop_rank_texture = flop_rank_texture
	event.turn_runout = turn_runout
	event.turn_action_sequence = turn_action_sequence
	event.river_runout = river_runout
	event.river_action_sequence = river_action_sequence
	event.hero_bet_river = hero_bet
	event.villain_fold_to_hero_bet = v_fold
	event.villain_raise_to_hero_bet = v_raise
	event.villain_bet_river = v_bet
	event.hero_fold_to_villain_bet = h_fold
	event.hero_raise_to_villain_bet = h_raise
	event.went_to_showdown = went_to_showdown
	event.showdown_type = showdown_type
	event.hero_won_showdown = hero_won
	event.pot_size_bb = pot_size_bb
	return event


def parse_line_event(lines: list[str]) -> LineEvent | None:
	board_type = parse_board_type(lines)
	if board_type is None:
		return None
	if not parse_hero_sees_flop(lines):
		return None

	pnl_result = parse_hero_pnl(lines)
	if pnl_result is None:
		return None
	hero_pnl_bb, hero_preflop_invested_bb = pnl_result

	pot_at_flop = parse_pot_at_flop(lines)
	if pot_at_flop is None or pot_at_flop <= 0:
		return None

	hero_is_pfr = parse_hero_preflop_raiser(lines)
	hero_ip = parse_hero_in_position(lines)

	# Parse flop actions (legacy for StreetStatsPanel)
	cbet, fold_to_cbet, raise_to_cbet, donk_bet, fold_to_donk_bet, raise_to_donk_bet, cbet_amount, donk_bet_amount = parse_flop_cbet(lines, hero_is_pfr)

	event = LineEvent()
	event.pot_type = parse_preflop_pot_type(lines)
	event.board_type = board_type
	event.hero_in_position = hero_ip
	event.hero_preflop_raiser = hero_is_pfr
	event.hero_pnl_bb = hero_pnl_bb
	event.hero_preflop_invested_bb = hero_preflop_invested_bb
	event.pot_at_flop_bb = pot_at_flop

	# Detailed flop action sequence
	event.flop_actions = parse_flop_actions_detailed(lines, hero_ip, pot_at_flop)

	# Legacy cbet/donk stats
	event.cbet = cbet
	event.fold_to_cbet = fold_to_cbet
	event.raise_to_cbet = raise_to_cbet
	event.donk_bet = donk_bet
	event.fold_to_donk_bet = fold_to_donk_bet
	event.raise_to_donk_bet = raise_to_donk_bet

	pot_dollars = pot_at_flop * 0.02
	if cbet_amount is not None:
		event.cbet_size_pct = (cbet_amount / pot_dollars) * 100
	if donk_bet_amount is not None:
		event.donk_bet_size_pct = (donk_bet_amount / pot_dollars) * 100

	event.fold_to_cbet_raise = _parse_fold_to_raise(lines, hero_is_pfr, is_cbet=True)
	event.fold_to_donk_raise = _parse_fold_to_raise(lines, hero_is_pfr, is_cbet=False)

	return event
