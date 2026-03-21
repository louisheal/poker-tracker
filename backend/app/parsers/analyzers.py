"""Analyzers: derive events from a HandAST with zero regex."""

import logging

from playing_cards_lib.core import Card
from playing_cards_lib.poker import PokerPosition

from app.models.enums import (
	ActionSequence, Runout,
	FlopRankTexture, ShowdownType,
	BoardType, PotType,
)
from app.models.events import RangeEvent, FlopEvent, TurnEvent, RiverEvent, LineEvent, FlopAction

from .ast import HandAST, HandContext, Action, ActionType

logger = logging.getLogger(__name__)

BB = 0.02

_ACTION_NAMES = {
	ActionType.FOLD: "folds",
	ActionType.CALL: "calls",
	ActionType.RAISE: "raises",
	ActionType.CHECK: "checks",
	ActionType.BET: "bets",
}


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def _classify_board(cards: list[Card]) -> BoardType:
	suits = {c.suit for c in cards}
	if len(suits) == 1:
		return BoardType.MONOTONE
	elif len(suits) == 2:
		return BoardType.TWO_TONE
	return BoardType.RAINBOW


def _classify_rank_texture(cards: list[Card]) -> FlopRankTexture:
	unique = len({c.rank for c in cards})
	if unique == 1:
		return FlopRankTexture.TRIPS
	elif unique == 2:
		return FlopRankTexture.PAIRED
	return FlopRankTexture.UNPAIRED


def _classify_turn_runout(flop_cards: list[Card], turn_card: Card) -> Runout:
	flop_ranks = {c.rank for c in flop_cards}
	flop_suits = {c.suit for c in flop_cards}

	if all(turn_card.rank.value > r.value for r in flop_ranks):
		return Runout.OVERCARD
	if turn_card.rank in flop_ranks:
		return Runout.PAIRED
	if turn_card.suit in flop_suits:
		suited_count = sum(1 for c in flop_cards if c.suit == turn_card.suit)
		if suited_count == 2:
			return Runout.FLUSH_COMPLETING
	return Runout.OTHER


def _classify_river_runout(flop_cards: list[Card], turn_card: Card, river_card: Card) -> Runout:
	board_ranks = {c.rank for c in flop_cards} | {turn_card.rank}
	board_suits = [c.suit for c in flop_cards] + [turn_card.suit]

	if all(river_card.rank.value > r.value for r in board_ranks):
		return Runout.OVERCARD
	if river_card.rank in board_ranks:
		return Runout.PAIRED
	if sum(1 for s in board_suits if s == river_card.suit) >= 2:
		return Runout.FLUSH_COMPLETING
	return Runout.OTHER


def _classify_showdown_type(actions: list[Action]) -> ShowdownType:
	has_bet = False
	has_raise = False
	for a in actions:
		if a.type == ActionType.BET:
			has_bet = True
		elif a.type == ActionType.RAISE:
			has_raise = True
	if has_raise:
		return ShowdownType.RAISE_OCCURRED
	if has_bet:
		return ShowdownType.BET_CALL
	return ShowdownType.CHECK_CHECK


# ---------------------------------------------------------------------------
# Shared computation helpers
# ---------------------------------------------------------------------------

def _compute_pot_type(preflop: list[Action]) -> PotType:
	raises = sum(1 for a in preflop if a.type == ActionType.RAISE)
	if raises >= 3:
		return PotType.FOUR_BET
	elif raises >= 2:
		return PotType.THREE_BET
	return PotType.SRP


def _compute_hero_pfr(preflop: list[Action]) -> bool:
	last_raiser = None
	for a in preflop:
		if a.type == ActionType.RAISE:
			last_raiser = a.player
	return last_raiser == "Hero"


def _compute_hero_ip(flop_actions: list[Action]) -> bool:
	if not flop_actions:
		return False
	return not flop_actions[0].is_hero


def _compute_pot_at_flop(ast: HandAST) -> float | None:
	contributions: dict[str, float] = {}
	for blind in ast.blinds:
		contributions[blind.player] = contributions.get(blind.player, 0) + blind.amount
	for action in ast.preflop:
		if action.type == ActionType.RAISE and action.raise_to is not None:
			contributions[action.player] = action.raise_to
		elif action.type in (ActionType.CALL, ActionType.BET) and action.amount is not None:
			contributions[action.player] = contributions.get(action.player, 0) + action.amount
	if not contributions:
		return None
	total = sum(contributions.values())
	return total / BB if total > 0 else None


def _compute_hero_pnl(ast: HandAST) -> tuple[float, float] | None:
	hero_invested = 0.0
	hero_round_invested = 0.0

	# Blinds
	for blind in ast.blinds:
		if blind.is_hero:
			hero_invested += blind.amount
			hero_round_invested += blind.amount

	# Preflop
	for action in ast.preflop:
		if not action.is_hero:
			continue
		if action.type in (ActionType.CALL, ActionType.BET) and action.amount:
			hero_invested += action.amount
			hero_round_invested += action.amount
		elif action.type == ActionType.RAISE and action.raise_to:
			new_money = action.raise_to - hero_round_invested
			hero_invested += new_money
			hero_round_invested = action.raise_to

	hero_preflop_invested = hero_invested

	# Post-flop streets
	for street in (ast.flop, ast.turn, ast.river):
		if street is None:
			continue
		hero_round_invested = 0.0
		for action in street.actions:
			if not action.is_hero:
				continue
			if action.type in (ActionType.CALL, ActionType.BET) and action.amount:
				hero_invested += action.amount
				hero_round_invested += action.amount
			elif action.type == ActionType.RAISE and action.raise_to:
				new_money = action.raise_to - hero_round_invested
				hero_invested += new_money
				hero_round_invested = action.raise_to

	# Uncalled bet
	if ast.uncalled_to == "Hero":
		hero_invested -= ast.uncalled_amount

	hero_collected = ast.hero_collected

	if hero_invested == 0.0 and hero_collected == 0.0:
		return None

	pnl_bb = (hero_collected - hero_invested) / BB
	preflop_bb = hero_preflop_invested / BB
	return (pnl_bb, preflop_bb)


def _compute_action_sequence(actions: list[Action], enum_cls, include_folds: bool = False):
	seq = ""
	for a in actions:
		if a.type == ActionType.CHECK:
			seq += "X"
		elif a.type == ActionType.BET:
			seq += "B"
		elif a.type == ActionType.RAISE:
			seq += "R"
		elif a.type == ActionType.CALL:
			seq += "C"
		elif a.type == ActionType.FOLD and include_folds:
			seq += "F"

	# Normalize folds to calls for sequence matching
	if include_folds:
		seq = seq.replace("F", "C")

	try:
		return enum_cls(seq)
	except ValueError:
		return None


# ---------------------------------------------------------------------------
# Cbet / donk analysis helpers
# ---------------------------------------------------------------------------

def _analyze_cbet_result(flop_actions: list[Action], hero_is_pfr: bool):
	cbet = False
	fold_to_cbet = False
	raise_to_cbet = False
	donk_bet = False
	fold_to_donk_bet = False
	raise_to_donk_bet = False
	cbet_amount: float | None = None
	donk_bet_amount: float | None = None

	for action in flop_actions:
		is_pfr = action.is_hero if hero_is_pfr else not action.is_hero

		if cbet and not is_pfr:
			if action.type == ActionType.FOLD:
				fold_to_cbet = True
			elif action.type == ActionType.RAISE:
				raise_to_cbet = True
			return cbet, fold_to_cbet, raise_to_cbet, donk_bet, fold_to_donk_bet, raise_to_donk_bet, cbet_amount, donk_bet_amount

		if donk_bet and is_pfr:
			if action.type == ActionType.FOLD:
				fold_to_donk_bet = True
			elif action.type == ActionType.RAISE:
				raise_to_donk_bet = True
			return cbet, fold_to_cbet, raise_to_cbet, donk_bet, fold_to_donk_bet, raise_to_donk_bet, cbet_amount, donk_bet_amount

		if cbet or donk_bet:
			continue

		if is_pfr and action.type == ActionType.BET:
			cbet = True
			cbet_amount = action.amount
			continue

		if not is_pfr and action.type == ActionType.BET:
			donk_bet = True
			donk_bet_amount = action.amount
			continue

	return cbet, fold_to_cbet, raise_to_cbet, donk_bet, fold_to_donk_bet, raise_to_donk_bet, cbet_amount, donk_bet_amount


def _analyze_fold_to_raise(flop_actions: list[Action], hero_is_pfr: bool, is_cbet: bool) -> bool:
	bet_seen = False
	raise_seen = False
	for action in flop_actions:
		is_pfr = action.is_hero if hero_is_pfr else not action.is_hero
		if is_cbet:
			if not bet_seen and is_pfr and action.type == ActionType.BET:
				bet_seen = True
			elif bet_seen and not raise_seen and not is_pfr and action.type == ActionType.RAISE:
				raise_seen = True
			elif raise_seen and is_pfr and action.type == ActionType.FOLD:
				return True
		else:
			if not bet_seen and not is_pfr and action.type == ActionType.BET:
				bet_seen = True
			elif bet_seen and not raise_seen and is_pfr and action.type == ActionType.RAISE:
				raise_seen = True
			elif raise_seen and not is_pfr and action.type == ActionType.FOLD:
				return True
	return False


def _build_flop_actions_detailed(flop_actions: list[Action], pot_at_flop_bb: float) -> list[FlopAction]:
	result: list[FlopAction] = []
	pot = pot_at_flop_bb * BB

	for action in flop_actions:
		actor = "hero" if action.is_hero else "villain"

		if action.type == ActionType.CHECK:
			result.append(FlopAction(actor=actor, action="X"))
		elif action.type == ActionType.FOLD:
			result.append(FlopAction(actor=actor, action="F"))
			break
		elif action.type == ActionType.BET:
			size_pct = None
			if action.amount and pot > 0:
				size_pct = round((action.amount / pot) * 100, 1)
				pot += action.amount
			result.append(FlopAction(actor=actor, action="B", size_pct=size_pct))
		elif action.type == ActionType.CALL:
			if action.amount:
				pot += action.amount
			result.append(FlopAction(actor=actor, action="C"))
		elif action.type == ActionType.RAISE:
			size_pct = None
			if action.raise_to and pot > 0:
				size_pct = round((action.raise_to / pot) * 100, 1)
			if action.amount:
				pot += action.amount
			result.append(FlopAction(actor=actor, action="R", size_pct=size_pct))

	return result


def _analyze_street_actions(actions: list[Action]):
	hero_bet = False
	v_fold = False
	v_raise = False
	v_bet = False
	h_fold = False
	h_raise = False

	for action in actions:
		if hero_bet and not action.is_hero:
			if action.type == ActionType.FOLD:
				v_fold = True
			elif action.type == ActionType.RAISE:
				v_raise = True
			return hero_bet, v_fold, v_raise, v_bet, h_fold, h_raise

		if v_bet and action.is_hero:
			if action.type == ActionType.FOLD:
				h_fold = True
			elif action.type == ActionType.RAISE:
				h_raise = True
			return hero_bet, v_fold, v_raise, v_bet, h_fold, h_raise

		if not hero_bet and not v_bet:
			if action.is_hero and action.type == ActionType.BET:
				hero_bet = True
			elif not action.is_hero and action.type == ActionType.BET:
				v_bet = True

	return hero_bet, v_fold, v_raise, v_bet, h_fold, h_raise


# ---------------------------------------------------------------------------
# build_context — compute all shared derived values once
# ---------------------------------------------------------------------------

def build_context(ast: HandAST) -> HandContext:
	ctx = HandContext(ast=ast)

	# Hero sees flop?
	ctx.hero_sees_flop = (
		ast.flop is not None
		and not any(a.is_hero and a.type == ActionType.FOLD for a in ast.preflop)
	)

	# Preflop-derived
	ctx.pot_type = _compute_pot_type(ast.preflop)
	ctx.hero_preflop_raiser = _compute_hero_pfr(ast.preflop)

	# Flop-derived
	if ast.flop:
		ctx.board_type = _classify_board(ast.flop.cards)
		ctx.flop_rank_texture = _classify_rank_texture(ast.flop.cards)
		ctx.hero_in_position = _compute_hero_ip(ast.flop.actions)
		ctx.flop_action_sequence = _compute_action_sequence(ast.flop.actions, ActionSequence)

	# Pot at flop
	pot = _compute_pot_at_flop(ast)
	if pot is not None:
		ctx.pot_at_flop_bb = pot

	# Hero PnL
	pnl = _compute_hero_pnl(ast)
	if pnl is not None:
		ctx.hero_pnl_bb, ctx.hero_preflop_invested_bb = pnl
		ctx.has_hero_pnl = True

	# Turn-derived
	if ast.turn and ast.flop:
		ctx.turn_runout = _classify_turn_runout(ast.flop.cards, ast.turn.cards[0])
		ctx.turn_action_sequence = _compute_action_sequence(ast.turn.actions, ActionSequence)

	# River-derived
	if ast.river and ast.turn and ast.flop:
		ctx.river_runout = _classify_river_runout(ast.flop.cards, ast.turn.cards[0], ast.river.cards[0])
		ctx.river_action_sequence = _compute_action_sequence(ast.river.actions, ActionSequence, include_folds=True)

	# Showdown
	ctx.went_to_showdown = ast.hero_showed_won is not None
	ctx.hero_won_showdown = ast.hero_showed_won is True
	ctx.pot_size_bb = ast.total_pot / BB
	if ctx.went_to_showdown and ast.river:
		ctx.showdown_type = _classify_showdown_type(ast.river.actions)

	return ctx


# ---------------------------------------------------------------------------
# Analyzer functions: HandAST/HandContext → Events
# ---------------------------------------------------------------------------

def analyze_range(ast: HandAST) -> list[RangeEvent]:
	if ast.hero_hole_cards is None:
		return []

	# Hero position = index of first hero action in preflop
	position = PokerPosition.BB
	for i, a in enumerate(ast.preflop):
		if a.is_hero:
			position = PokerPosition(i)
			break

	events: list[RangeEvent] = []
	pot_type = PotType.SRP
	v_pos = 0
	villain = None

	for action in ast.preflop:
		if action.is_hero and action.type == ActionType.CHECK:
			return events

		if not action.is_hero and action.type == ActionType.FOLD:
			v_pos += 1
			continue

		if pot_type == PotType.SRP:
			if action.is_hero:
				events.append(RangeEvent(
					played_on=ast.played_on,
					hand_key=ast.hero_hole_cards.key(),
					position=position,
					action=_ACTION_NAMES[action.type],
					pot_type=pot_type,
					villain=None,
				))
				pot_type = PotType.FOUR_BET
				continue
			else:
				villain = PokerPosition(v_pos)
				pot_type = PotType.THREE_BET
				continue

		if pot_type == PotType.THREE_BET:
			if action.is_hero:
				events.append(RangeEvent(
					played_on=ast.played_on,
					hand_key=ast.hero_hole_cards.key(),
					position=position,
					action=_ACTION_NAMES[action.type],
					pot_type=pot_type,
					villain=villain,
				))
				return events
			if action.type == ActionType.RAISE:
				pot_type = PotType.FOUR_BET
				continue

		if pot_type == PotType.FOUR_BET:
			if action.is_hero:
				events.append(RangeEvent(
					played_on=ast.played_on,
					hand_key=ast.hero_hole_cards.key(),
					position=position,
					action=_ACTION_NAMES[action.type],
					pot_type=pot_type,
					villain=None,
				))
				return events
			if action.type == ActionType.RAISE:
				return events

	return events


def analyze_cbet(ctx: HandContext) -> FlopEvent | None:
	if ctx.board_type is None or not ctx.hero_sees_flop:
		return None

	flop_actions = ctx.ast.flop.actions
	(cbet, fold_to_cbet, raise_to_cbet,
	 donk_bet, fold_to_donk_bet, raise_to_donk_bet,
	 cbet_amount, donk_bet_amount) = _analyze_cbet_result(flop_actions, ctx.hero_preflop_raiser)

	event = FlopEvent(
		played_on=ctx.ast.played_on,
		pot_type=ctx.pot_type,
		board_type=ctx.board_type,
		hero_preflop_raiser=ctx.hero_preflop_raiser,
		hero_in_position=ctx.hero_in_position,
		cbet=cbet,
		fold_to_cbet=fold_to_cbet,
		raise_to_cbet=raise_to_cbet,
		donk_bet=donk_bet,
		fold_to_donk_bet=fold_to_donk_bet,
		raise_to_donk_bet=raise_to_donk_bet,
		cbet_size_pct=None,
		donk_bet_size_pct=None,
	)

	if ctx.pot_at_flop_bb > 0:
		pot_dollars = ctx.pot_at_flop_bb * BB
		if cbet_amount is not None:
			event.cbet_size_pct = (cbet_amount / pot_dollars) * 100
		if donk_bet_amount is not None:
			event.donk_bet_size_pct = (donk_bet_amount / pot_dollars) * 100

	return event


def analyze_turn(ctx: HandContext) -> TurnEvent | None:
	if ctx.board_type is None or not ctx.hero_sees_flop:
		return None
	if ctx.flop_action_sequence is None:
		return None
	if ctx.turn_runout is None:
		return None

	turn_actions = ctx.ast.turn.actions
	(hero_bet, v_fold, v_raise,
	 v_bet, h_fold, h_raise) = _analyze_street_actions(turn_actions)

	event = TurnEvent(
		played_on=ctx.ast.played_on,
		pot_type=ctx.pot_type,
		board_type=ctx.board_type,
		hero_preflop_raiser=ctx.hero_preflop_raiser,
		hero_in_position=ctx.hero_in_position,
		flop_action_sequence=ctx.flop_action_sequence,
		turn_runout=ctx.turn_runout,
		hero_bet_turn=hero_bet,
		villain_fold_to_hero_bet=v_fold,
		villain_raise_to_hero_bet=v_raise,
		villain_bet_turn=v_bet,
		hero_fold_to_villain_bet=h_fold,
		hero_raise_to_villain_bet=h_raise,
	)
	return event


def analyze_river(ctx: HandContext) -> RiverEvent | None:
	ast = ctx.ast
	if ctx.board_type is None or not ctx.hero_sees_flop:
		return None
	if ast.river is None:
		return None
	if ctx.flop_action_sequence is None or ctx.flop_rank_texture is None:
		return None
	if ctx.turn_runout is None or ctx.turn_action_sequence is None:
		return None
	if ctx.river_runout is None or ctx.river_action_sequence is None:
		return None

	river_actions = ast.river.actions
	(hero_bet, v_fold, v_raise,
	 v_bet, h_fold, h_raise) = _analyze_street_actions(river_actions)

	event = RiverEvent(
		played_on=ast.played_on,
		pot_type=ctx.pot_type,
		board_type=ctx.board_type,
		hero_in_position=ctx.hero_in_position,
		flop_action_sequence=ctx.flop_action_sequence,
		flop_rank_texture=ctx.flop_rank_texture,
		turn_runout=ctx.turn_runout,
		turn_action_sequence=ctx.turn_action_sequence,
		river_runout=ctx.river_runout,
		river_action_sequence=ctx.river_action_sequence,
		hero_bet_river=hero_bet,
		villain_fold_to_hero_bet=v_fold,
		villain_raise_to_hero_bet=v_raise,
		villain_bet_river=v_bet,
		hero_fold_to_villain_bet=h_fold,
		hero_raise_to_villain_bet=h_raise,
		went_to_showdown=ctx.went_to_showdown,
		showdown_type=ctx.showdown_type,
		hero_won_showdown=ctx.hero_won_showdown,
		pot_size_bb=ctx.pot_size_bb,
	)
	return event


def analyze_line(ctx: HandContext) -> LineEvent | None:
	ast = ctx.ast
	if ctx.board_type is None or not ctx.hero_sees_flop:
		return None
	if not ctx.has_hero_pnl:
		return None
	if ctx.pot_at_flop_bb <= 0:
		return None

	flop_actions = ast.flop.actions
	hero_is_pfr = ctx.hero_preflop_raiser

	(cbet, fold_to_cbet, raise_to_cbet,
	 donk_bet, fold_to_donk_bet, raise_to_donk_bet,
	 cbet_amount, donk_bet_amount) = _analyze_cbet_result(flop_actions, hero_is_pfr)

	flop_actions_detailed = _build_flop_actions_detailed(flop_actions, ctx.pot_at_flop_bb)
	pot_dollars = ctx.pot_at_flop_bb * BB
	
	cbet_size = None
	if cbet_amount is not None:
		cbet_size = (cbet_amount / pot_dollars) * 100
	
	donk_size = None
	if donk_bet_amount is not None:
		donk_size = (donk_bet_amount / pot_dollars) * 100

	event = LineEvent(
		played_on=ast.played_on,
		pot_type=ctx.pot_type,
		board_type=ctx.board_type,
		hero_in_position=ctx.hero_in_position,
		hero_preflop_raiser=hero_is_pfr,
		hero_pnl_bb=ctx.hero_pnl_bb,
		hero_preflop_invested_bb=ctx.hero_preflop_invested_bb,
		pot_at_flop_bb=ctx.pot_at_flop_bb,
		flop_actions=flop_actions_detailed,
		cbet=cbet,
		fold_to_cbet=fold_to_cbet,
		raise_to_cbet=raise_to_cbet,
		donk_bet=donk_bet,
		fold_to_donk_bet=fold_to_donk_bet,
		raise_to_donk_bet=raise_to_donk_bet,
		cbet_size_pct=cbet_size,
		donk_bet_size_pct=donk_size,
		fold_to_cbet_raise=_analyze_fold_to_raise(flop_actions, hero_is_pfr, is_cbet=True),
		fold_to_donk_raise=_analyze_fold_to_raise(flop_actions, hero_is_pfr, is_cbet=False),
	)

	return event
