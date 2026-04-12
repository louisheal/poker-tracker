"""Solver EV calculator -- computes expected value for each hero hand
at a decision point using the trained model's villain response predictions.

Different from app/parsers/ev_calculator.py which uses empirical data.
This version uses the transformer model to predict villain behavior.
"""

from __future__ import annotations

import torch

from playing_cards_lib.core import Card, Rank, Suit
from app.models.enums import Action

from solver.model import SolverTransformer
from solver.models import Token, TokenType
from solver.dataset import (
    MAX_SEQ_LEN,
    RANK_TO_INDEX, SUIT_TO_INDEX, ACTION_TO_INDEX,
)
from solver.ranges import (
    get_starting_range,
    filter_range_by_equity,
    _normalize_combo,
    _cards_conflict,
)
from solver.eq_calculator import all_hands_vs_range

POSTFLOP_POSITION_ORDER = ["SB", "BB", "LJ", "HJ", "CO", "BTN"]

# Assumed villain sizing for one-level lookahead EV estimation
VILLAIN_BET_SIZE_PCT = 66    # Villain bets 66% pot after hero checks
VILLAIN_RAISE_MULTIPLIER = 3  # Villain raises to 3× hero's bet


def compute_check_ev(
    pot_bb: float,
    check_back_pct: float,
    villain_bet_pct: float,
    eq_vs_checking: float,
    eq_vs_betting: float,
    v_bet_bb: float,
) -> float:
    """Compute EV when hero checks with one-level lookahead.

    Villain either checks back (showdown) or bets, and hero optimally
    calls or folds when facing the bet.
    """
    check_back_ev = eq_vs_checking * pot_bb
    call_ev = eq_vs_betting * (pot_bb + 2 * v_bet_bb) - v_bet_bb
    facing_bet_ev = max(0.0, call_ev)
    return check_back_pct * check_back_ev + villain_bet_pct * facing_bet_ev


def compute_aggressive_ev(
    pot_bb: float,
    bet_bb: float,
    fold_pct: float,
    call_pct: float,
    raise_pct: float,
    eq_vs_callers: float,
    eq_vs_raising: float,
    v_raise_bb: float,
    call_amount_bb: float = 0.0,
) -> float:
    """Compute EV when hero bets/raises with one-level lookahead.

    Villain folds, calls, or raises. When villain raises, hero optimally
    calls or folds.

    call_amount_bb: the villain's prior bet that hero is raising over.
    When > 0, pot_bb already includes this amount, so we subtract it
    from the total pot to avoid double-counting.
    """
    # Total pot when villain calls hero's bet/raise
    # pot_bb includes villain's prior bet (call_amount_bb), and villain
    # matches hero's bet_bb, so villain adds (bet_bb - call_amount_bb)
    pot_if_called = pot_bb + 2 * bet_bb - call_amount_bb

    hero_call_amount = v_raise_bb - bet_bb
    fold_ev = -bet_bb
    # Pot when villain re-raises and hero calls:
    # pot_bb + bet_bb + v_raise_bb + hero_call_amount - call_amount_bb
    pot_if_reraised = pot_bb + bet_bb + v_raise_bb + hero_call_amount - call_amount_bb
    call_raise_ev = eq_vs_raising * pot_if_reraised - (bet_bb + hero_call_amount)
    raise_branch_ev = max(fold_ev, call_raise_ev)

    return (
        fold_pct * pot_bb
        + call_pct * (eq_vs_callers * pot_if_called - bet_bb)
        + raise_pct * raise_branch_ev
    )


# Hero action set matching frontend types.ts
HERO_ACTIONS_PREFLOP = ["Fold", "Call", "Raise"]
HERO_ACTIONS_OPEN = ["Check", "B33", "B50", "B66", "B100", "B133", "B200"]
HERO_ACTIONS_FACING_BET = ["Fold", "Call", "R3x", "R4x", "R5x"]

ACTION_TO_BET_PCT: dict[str, float] = {
    "Check": 0.0,
    "Fold": 0.0,
    "Call": 0.0,
    "Raise": 300.0,  # Preflop raise ~3x
    "B33": 33.0,
    "B50": 50.0,
    "B66": 66.0,
    "B100": 100.0,
    "B133": 133.0,
    "B200": 200.0,
    "R3x": 300.0,
    "R4x": 400.0,
    "R5x": 500.0,
}

# When facing a postflop bet, R3x/R4x/R5x are N× the villain's bet (not N× pot)
RAISE_MULTIPLIER: dict[str, float] = {
    "R3x": 3.0,
    "R4x": 4.0,
    "R5x": 5.0,
}


def _action_key_to_model_action(action_key: str) -> int:
    """Map a hero action key to the model's action index."""
    mapping = {
        "Fold": ACTION_TO_INDEX[Action.FOLD],
        "Check": ACTION_TO_INDEX[Action.CHECK],
        "Call": ACTION_TO_INDEX[Action.CALL],
        "Raise": ACTION_TO_INDEX[Action.RAISE],
    }
    if action_key in mapping:
        return mapping[action_key]
    if action_key.startswith("B"):
        return ACTION_TO_INDEX[Action.BET]
    if action_key.startswith("R"):
        return ACTION_TO_INDEX[Action.RAISE]
    return ACTION_TO_INDEX[Action.CHECK]


def _action_to_token(action_str: str) -> Token:
    """Parse a 'POS:ACTION' string into a Token."""
    parts = action_str.split(":")
    action_key = parts[-1] if len(parts) > 1 else parts[0]
    bet_pct = ACTION_TO_BET_PCT.get(action_key, 0.0)
    model_action = _action_key_to_model_action(action_key)
    return Token(TokenType.ACTION, action=model_action, bet_size_pct=bet_pct)


def _card_token(card: Card) -> Token:
    return Token(TokenType.CARD, rank=RANK_TO_INDEX[card.rank], suit=SUIT_TO_INDEX[card.suit])


def _split_postflop_by_street(postflop_actions: list[str]) -> list[list[str]]:
    """Split flat postflop action list into per-street lists.

    Street ends after: Call, Fold, or two consecutive Checks.
    """
    if not postflop_actions:
        return []

    streets: list[list[str]] = [[]]
    for action_str in postflop_actions:
        action_key = action_str.split(":")[-1]
        streets[-1].append(action_str)

        if action_key == "Fold":
            break
        if action_key == "Call":
            streets.append([])
        elif action_key == "Check" and len(streets[-1]) >= 2:
            prev_key = streets[-1][-2].split(":")[-1]
            if prev_key == "Check":
                streets.append([])

    return [s for s in streets if s]


def _build_sequence_tokens(
    board: list[Card],
    action_prefix: list[str],
) -> list[Token]:
    """Build the token sequence up to the current decision point.

    Correct ordering: preflop actions, then for each street:
    street marker + board cards + street actions.
    """
    tokens: list[Token] = []

    # Separate preflop from postflop actions
    preflop_actions: list[str] = []
    postflop_actions: list[str] = []
    for action_str in action_prefix:
        label = action_str.split(":")[0] if ":" in action_str else ""
        if label in ("OOP", "IP"):
            postflop_actions.append(action_str)
        else:
            preflop_actions.append(action_str)

    # Preflop actions
    for action_str in preflop_actions:
        tokens.append(_action_to_token(action_str))

    # Split postflop actions by street
    street_actions = _split_postflop_by_street(postflop_actions)

    # Board cards grouped by street
    board_streets: list[tuple[int, list[Card]]] = []
    if len(board) >= 3:
        board_streets.append((0, board[:3]))
    if len(board) >= 4:
        board_streets.append((1, [board[3]]))
    if len(board) >= 5:
        board_streets.append((2, [board[4]]))

    # Interleave: street marker + board cards + street actions
    for i, (marker, cards) in enumerate(board_streets):
        tokens.append(Token(TokenType.STREET_MARKER, action=marker))
        for card in cards:
            tokens.append(_card_token(card))
        if i < len(street_actions):
            for action_str in street_actions[i]:
                tokens.append(_action_to_token(action_str))

    return tokens


def _tensorize_sequence(tokens: list[Token]) -> dict[str, torch.Tensor]:
    """Convert a token list to a batch-of-1 tensor dict for the model."""
    seq = tokens[:MAX_SEQ_LEN]
    length = len(seq)

    token_types = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.long)
    ranks = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.long)
    suits = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.long)
    actions = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.long)
    bet_sizes = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.float)
    street_ids = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.long)
    padding_mask = torch.ones(1, MAX_SEQ_LEN, dtype=torch.bool)

    for i, tok in enumerate(seq):
        token_types[0, i] = int(tok.token_type)
        ranks[0, i] = tok.rank
        suits[0, i] = tok.suit
        actions[0, i] = tok.action
        bet_sizes[0, i] = tok.bet_size_pct
        street_ids[0, i] = tok.action if tok.token_type == TokenType.STREET_MARKER else 0
        padding_mask[0, i] = False

    return {
        "token_types": token_types,
        "ranks": ranks,
        "suits": suits,
        "actions": actions,
        "bet_sizes": bet_sizes,
        "street_ids": street_ids,
        "padding_mask": padding_mask,
    }


def _combo_to_hand_key(combo: tuple[Card, Card]) -> str:
    """Convert a specific combo to its canonical hand key (e.g. AKs, QQ, T9o).

    Higher rank always comes first (A before K, K before Q, etc.).
    """
    r1, r2 = combo[0].rank, combo[1].rank
    rank_order = list(Rank)
    i1, i2 = rank_order.index(r1), rank_order.index(r2)
    same_suit = combo[0].suit == combo[1].suit

    if r1 == r2:
        return f"{r1.value}{r2.value}"

    # Higher index = higher rank (2=0, A=12), so put higher index first
    if i1 > i2:
        return f"{r1.value}{r2.value}{'s' if same_suit else 'o'}"
    else:
        return f"{r2.value}{r1.value}{'s' if same_suit else 'o'}"


def _generate_all_combos() -> list[tuple[Card, Card]]:
    """Generate all 1326 unique hole card combos."""
    cards = [Card(r, s) for r in Rank for s in Suit]
    combos = []
    for i in range(len(cards)):
        for j in range(i + 1, len(cards)):
            combos.append((cards[i], cards[j]))
    return combos


ALL_COMBOS = _generate_all_combos()


def _determine_oop_ip(pos1: str, pos2: str) -> tuple[str, str]:
    """Return (OOP, IP) based on postflop position order."""
    i1 = POSTFLOP_POSITION_ORDER.index(pos1) if pos1 in POSTFLOP_POSITION_ORDER else 0
    i2 = POSTFLOP_POSITION_ORDER.index(pos2) if pos2 in POSTFLOP_POSITION_ORDER else 0
    if i1 < i2:
        return pos1, pos2
    return pos2, pos1


def _is_opening_action(prior_action_keys: list[str]) -> bool:
    """Whether the current decision is an opening (check/bet) vs response (fold/call/raise)."""
    if not prior_action_keys:
        return True
    last = prior_action_keys[-1]
    return last == "Check"


def compute_current_ranges(
    model: SolverTransformer,
    board: list[Card],
    street: str,
    action_prefix: list[str],
    hero_position: str,
    villain_position: str,
    pot_type: str,
) -> tuple[dict[tuple[Card, Card], float], dict[tuple[Card, Card], float]]:
    """Compute current ranges for hero and villain, narrowed by prior postflop actions.

    Walks through each postflop action in the prefix. For each action,
    runs the model to predict action probabilities at that decision point,
    then uses equity-based filtering to keep only the sub-range matching
    the action that was actually taken.

    Returns (hero_range, villain_range).
    """
    hero_range = get_starting_range(hero_position, pot_type, vs_position=villain_position)
    villain_range = get_starting_range(villain_position, pot_type, vs_position=hero_position)

    if not board or street == "preflop":
        return hero_range, villain_range

    oop_pos, ip_pos = _determine_oop_ip(hero_position, villain_position)

    # Split actions into preflop (position labels) and postflop (OOP/IP labels)
    preflop_actions: list[str] = []
    postflop_actions: list[tuple[str, str]] = []

    for action_str in action_prefix:
        parts = action_str.split(":")
        if len(parts) > 1:
            label, action_key = parts[0], parts[1]
        else:
            label, action_key = "", parts[0]

        if label in ("OOP", "IP"):
            postflop_actions.append((label, action_key))
        else:
            preflop_actions.append(action_str)

    label_to_pos = {"OOP": oop_pos, "IP": ip_pos}

    # Map each postflop action index to its street (0=flop, 1=turn, 2=river)
    postflop_strs = [f"{l}:{a}" for l, a in postflop_actions]
    street_groups = _split_postflop_by_street(postflop_strs)
    action_to_street: dict[int, int] = {}
    idx = 0
    for street_idx, group in enumerate(street_groups):
        for _ in group:
            action_to_street[idx] = street_idx
            idx += 1

    # Board slices per street: flop=3 cards, turn=4, river=5
    BOARD_SIZES = {0: 3, 1: 4, 2: 5}

    for i, (label, action_key) in enumerate(postflop_actions):
        if action_key == "Fold":
            continue

        pos = label_to_pos.get(label, "")

        # Only include board cards known at this action's street
        action_street = action_to_street.get(i, 0)
        board_at_action = board[:BOARD_SIZES.get(action_street, len(board))]

        # Build sequence up to this decision point (before this action)
        prior_postflop = [f"{l}:{a}" for l, a in postflop_actions[:i]]
        tokens = _build_sequence_tokens(board_at_action, preflop_actions + prior_postflop)

        with torch.no_grad():
            batch = _tensorize_sequence(tokens)
            logits = model(batch)
            probs = torch.softmax(logits, dim=-1).cpu()[0]

        range_to_narrow = hero_range if pos == hero_position else villain_range

        # Only look at prior actions on the SAME street to determine opening vs facing bet
        same_street_actions = [
            a for j, (_, a) in enumerate(postflop_actions[:i])
            if action_to_street.get(j, 0) == action_street
        ]
        is_opening = _is_opening_action(same_street_actions)

        street_name = ["flop", "turn", "river"][action_street]

        if is_opening:
            check_pct = probs[1].item()
            bet_pct = probs[3].item() + probs[4].item()
            total = check_pct + bet_pct
            if total > 0:
                check_pct /= total
                bet_pct /= total

            # Split: top by equity = betting, rest = checking
            betting_range, _, checking_range = filter_range_by_equity(
                range_to_narrow, board_at_action, street_name,
                raise_pct=bet_pct * 100,
                call_pct=0,
            )

            narrowed = checking_range if action_key == "Check" else betting_range
        else:
            fold_pct = probs[0].item()
            call_pct = probs[1].item() + probs[2].item()
            raise_pct = probs[3].item() + probs[4].item()
            total = fold_pct + call_pct + raise_pct
            if total > 0:
                fold_pct /= total
                call_pct /= total
                raise_pct /= total

            raising_range, calling_range, folding_range = filter_range_by_equity(
                range_to_narrow, board_at_action, street_name,
                raise_pct=raise_pct * 100,
                call_pct=call_pct * 100,
            )

            if action_key == "Call":
                narrowed = calling_range
            elif action_key.startswith("R") or action_key == "Raise":
                narrowed = raising_range
            else:
                narrowed = folding_range

        if pos == hero_position:
            hero_range = narrowed
        else:
            villain_range = narrowed

    return hero_range, villain_range


def _aggregate_to_hand_keys(
    combo_range: dict[tuple[Card, Card], float],
) -> dict[str, float]:
    """Aggregate a combo-keyed range to hand keys for debug display."""
    key_freqs: dict[str, list[float]] = {}
    for combo, freq in combo_range.items():
        hk = _combo_to_hand_key(combo)
        key_freqs.setdefault(hk, []).append(freq)
    return {k: round(sum(vs) / len(vs), 2) for k, vs in key_freqs.items() if sum(vs) > 0}


def solve_spot(
    model: SolverTransformer,
    board: list[Card],
    street: str,
    action_prefix: list[str],
    hero_position: str,
    villain_position: str,
    pot_type: str,
    pot_bb: float,
    hero_actions: list[str],
) -> dict:
    """Run the solver for a single spot.

    For each hero action, uses the model to predict villain's response,
    then computes EV at the combo level (not hand-key level) so that
    suit-sensitive draws are handled correctly on textured boards.

    Returns a SolverResult dict with:
      - hands: per-hand-key best action + EVs + combo details
      - actions: per-action summary (avg EV, count)
      - totalHands: number of hand keys evaluated
      - debug: per-player current ranges + model output
    """
    # Compute current ranges (narrowed by prior postflop actions)
    hero_range, villain_range = compute_current_ranges(
        model, board, street, action_prefix,
        hero_position, villain_position, pot_type,
    )

    # Filter combos that don't conflict with the board
    valid_combos = [c for c in ALL_COMBOS if not _cards_conflict(c, board)]

    # Compute equity vs full villain range for each combo (for display)
    combo_equity: dict[tuple[Card, Card], float] = {}
    if board and street != "preflop":
        combo_equity = all_hands_vs_range(valid_combos, villain_range, board)

    # Per-combo results: combo -> {action_key -> ev}
    combo_evs: dict[tuple[Card, Card], dict[str, float]] = {c: {} for c in valid_combos}

    debug_model_output: dict[str, dict[str, float]] = {}

    # Compute call cost from the last villain action (needed for Call EV).
    # When "Call" is in hero_actions, the last action is always a villain bet/raise.
    call_amount_bb = 0.0
    if action_prefix:
        last_action_key = action_prefix[-1].split(":")[-1]
        last_bet_pct = ACTION_TO_BET_PCT.get(last_action_key, 0.0)
        if last_bet_pct > 0:
            pot_before_villain = pot_bb / (1.0 + last_bet_pct / 100.0)
            call_amount_bb = pot_before_villain * last_bet_pct / 100.0

    for action_key in hero_actions:
        # For raises facing a bet, compute size as multiplier of villain's bet
        if action_key in RAISE_MULTIPLIER and call_amount_bb > 0:
            multiplier = RAISE_MULTIPLIER[action_key]
            bet_bb = multiplier * call_amount_bb
            bet_pct = (bet_bb / pot_bb) * 100 if pot_bb > 0 else 0.0
        else:
            bet_pct = ACTION_TO_BET_PCT.get(action_key, 0.0)
            bet_bb = (bet_pct / 100.0) * pot_bb

        # Build sequence (no hole cards)
        base_tokens = _build_sequence_tokens(board, action_prefix)
        model_action = _action_key_to_model_action(action_key)
        hero_token = Token(TokenType.ACTION, action=model_action, bet_size_pct=bet_pct)
        full_tokens = base_tokens + [hero_token]

        # Run model once per action (same for all combos -- no hole cards in input)
        with torch.no_grad():
            batch = _tensorize_sequence(full_tokens)
            logits = model(batch)
            probs = torch.softmax(logits, dim=-1).cpu()[0]

        fold_pct = probs[0].item()
        # When hero bets/raises, villain can fold/call/raise (CHECK+CALL = continue).
        # When hero checks/calls, villain responds to that — only CALL is "continue."
        is_aggressive = action_key not in ("Fold", "Check", "Call")
        if is_aggressive:
            call_pct = probs[2].item() + probs[1].item()
        else:
            call_pct = probs[2].item()
        raise_pct = probs[3].item() + probs[4].item()

        total = fold_pct + call_pct + raise_pct
        if total > 0:
            fold_pct /= total
            call_pct /= total
            raise_pct /= total

        debug_model_output[action_key] = {
            "raw_fold": round(probs[0].item(), 4),
            "raw_check": round(probs[1].item(), 4),
            "raw_call": round(probs[2].item(), 4),
            "raw_bet": round(probs[3].item(), 4),
            "raw_raise": round(probs[4].item(), 4),
            "villain_fold_pct": round(fold_pct * 100, 1),
            "villain_call_pct": round(call_pct * 100, 1),
            "villain_raise_pct": round(raise_pct * 100, 1),
            "bet_size_bb": round(bet_bb, 2),
            "bet_size_pct_pot": round(bet_pct, 1),
        }

        # Determine equity ranges and compute EV per combo
        can_compute_equity = street != "preflop" and bool(board)
        default_eq: dict[tuple[Card, Card], float] = {
            _normalize_combo(c): 0.5 for c in valid_combos
        }

        if action_key == "Fold":
            for combo in valid_combos:
                combo_evs[combo][action_key] = 0.0

        elif action_key == "Check":
            # One-level lookahead: villain checks back or bets after hero check
            raw_check = probs[1].item()
            raw_call = probs[2].item()
            raw_bet = probs[3].item()
            raw_raise = probs[4].item()
            check_back_pct = raw_check + raw_call
            villain_bet_pct = raw_bet + raw_raise
            total_check = check_back_pct + villain_bet_pct
            if total_check > 0:
                check_back_pct /= total_check
                villain_bet_pct /= total_check

            v_bet_bb = (VILLAIN_BET_SIZE_PCT / 100.0) * pot_bb

            if can_compute_equity and villain_range:
                # Split villain into betting vs checking sub-ranges
                betting_range, checking_range, _ = filter_range_by_equity(
                    villain_range, board, street,
                    raise_pct=villain_bet_pct * 100,
                    call_pct=check_back_pct * 100,
                )
                eq_vs_checking = all_hands_vs_range(valid_combos, checking_range, board) if checking_range else default_eq
                eq_vs_betting = all_hands_vs_range(valid_combos, betting_range, board) if betting_range else default_eq
            else:
                eq_vs_checking = default_eq
                eq_vs_betting = default_eq

            for combo in valid_combos:
                nc = _normalize_combo(combo)
                eq_chk = eq_vs_checking.get(nc, 0.5)
                eq_bet = eq_vs_betting.get(nc, 0.5)

                ev = compute_check_ev(pot_bb, check_back_pct, villain_bet_pct, eq_chk, eq_bet, v_bet_bb)
                combo_evs[combo][action_key] = round(ev, 2)

        elif action_key == "Call":
            eq_map = all_hands_vs_range(valid_combos, villain_range, board) if can_compute_equity and villain_range else default_eq
            for combo in valid_combos:
                eq_vs_callers = eq_map.get(_normalize_combo(combo), 0.5)
                ev = eq_vs_callers * (pot_bb + call_amount_bb) - call_amount_bb
                combo_evs[combo][action_key] = round(ev, 2)

        else:
            # Aggressive action (bet/raise): villain folds/calls/raises
            if can_compute_equity and villain_range:
                raising_range, calling_range, folding_range = filter_range_by_equity(
                    villain_range, board, street,
                    raise_pct=raise_pct * 100,
                    call_pct=call_pct * 100,
                )
                eq_vs_callers_map = all_hands_vs_range(valid_combos, calling_range, board) if calling_range else default_eq

                # One-level lookahead for raise branch: hero can call or fold
                v_raise_bb = VILLAIN_RAISE_MULTIPLIER * bet_bb
                hero_call_amount = v_raise_bb - bet_bb
                if raising_range and raise_pct > 0:
                    eq_vs_raising_map = all_hands_vs_range(valid_combos, raising_range, board)
                else:
                    eq_vs_raising_map = default_eq
            else:
                eq_vs_callers_map = default_eq
                eq_vs_raising_map = default_eq
                v_raise_bb = VILLAIN_RAISE_MULTIPLIER * bet_bb
                hero_call_amount = v_raise_bb - bet_bb

            for combo in valid_combos:
                nc = _normalize_combo(combo)
                eq_vs_callers = eq_vs_callers_map.get(nc, 0.5)
                eq_vs_raising = eq_vs_raising_map.get(nc, 0.5)

                ev = compute_aggressive_ev(
                    pot_bb, bet_bb, fold_pct, call_pct, raise_pct,
                    eq_vs_callers, eq_vs_raising, v_raise_bb,
                    call_amount_bb=call_amount_bb,
                )
                combo_evs[combo][action_key] = round(ev, 2)

    # Group combos into hand keys
    hands: dict[str, dict] = {}

    for combo in valid_combos:
        hand_key = _combo_to_hand_key(combo)
        evs = combo_evs[combo]
        best_action = max(evs, key=lambda k: evs[k]) if evs else ""
        card_str = (
            f"{combo[0].rank.value}{combo[0].suit.value}"
            f"{combo[1].rank.value}{combo[1].suit.value}"
        )

        combo_result = {
            "combo": card_str,
            "bestAction": best_action,
            "ev": evs.get(best_action, 0.0),
            "evs": dict(evs),
            "equity": round(combo_equity.get(_normalize_combo(combo), 0.5), 3),
        }

        if hand_key not in hands:
            hands[hand_key] = {"evs": {}, "bestAction": "", "combos": []}
        hands[hand_key]["combos"].append(combo_result)

    # Compute hand-key level evs as average across combos
    for hand_key, data in hands.items():
        combos_list = data["combos"]
        if not combos_list:
            continue

        for action_key in hero_actions:
            action_evs = [c["evs"].get(action_key, 0.0) for c in combos_list]
            data["evs"][action_key] = round(sum(action_evs) / len(action_evs), 2)

        data["bestAction"] = max(data["evs"], key=lambda k: data["evs"][k]) if data["evs"] else ""

        combo_equities = [c["equity"] for c in combos_list]
        data["equity"] = round(sum(combo_equities) / len(combo_equities), 3)

    # Action summaries
    action_summaries: dict[str, dict] = {}
    for action_key in hero_actions:
        ev_sum = sum(d["evs"].get(action_key, 0.0) for d in hands.values())
        action_summaries[action_key] = {
            "avgEv": round(ev_sum / max(len(hands), 1), 2),
            "bestActionCount": 0,
        }

    for data in hands.values():
        best = data["bestAction"]
        if best in action_summaries:
            action_summaries[best]["bestActionCount"] += 1

    # Add actionCounts per hand key (combo-level action distribution)
    for hand_key, data in hands.items():
        counts: dict[str, int] = {}
        for c in data["combos"]:
            ba = c["bestAction"]
            counts[ba] = counts.get(ba, 0) + 1
        data["actionCounts"] = counts

    oop_pos, ip_pos = _determine_oop_ip(hero_position, villain_position)

    oop_range = hero_range if hero_position == oop_pos else villain_range
    ip_range = hero_range if hero_position == ip_pos else villain_range

    return {
        "hands": hands,
        "actions": action_summaries,
        "totalHands": len(hands),
        "debug": {
            "oopRange": _aggregate_to_hand_keys(oop_range),
            "ipRange": _aggregate_to_hand_keys(ip_range),
            "oopPosition": oop_pos,
            "ipPosition": ip_pos,
            "modelOutput": debug_model_output,
            "potBB": round(pot_bb, 2),
            "callAmountBB": round(call_amount_bb, 2),
        },
    }
