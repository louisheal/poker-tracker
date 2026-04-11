import pytest
from datetime import date

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards

from app.models.events import LineEvent, StreetAction
from app.models.enums import PotType, BoardType, MadeHandType, FlushDrawType, StraightDrawType
from app.models.filters import LineFilter
from app.models.stores import LineEvents
from app.parsers.equity import VALID_TRIPLES


RANK_MAP = {
    "2": Rank.TWO, "3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
    "6": Rank.SIX, "7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE,
    "T": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN, "K": Rank.KING, "A": Rank.ACE,
}
SUIT_MAP = {"h": Suit.HEARTS, "d": Suit.DIAMONDS, "s": Suit.SPADES, "c": Suit.CLUBS}

ALL_FILTER = LineFilter()


def _c(rank_str: str, suit_str: str) -> Card:
    return Card(RANK_MAP[rank_str], SUIT_MAP[suit_str])


def _make_event(
    flop_actions: list[StreetAction],
    flop_cards: list[Card],
    villain_hand: HoleCards | None = None,
    hero_hand: HoleCards | None = None,
    pot_at_flop_bb: float = 6.0,
) -> LineEvent:
    """Create a minimal LineEvent for ev_node_data tests."""
    return LineEvent(
        played_on=date(2025, 1, 1),
        pot_type=PotType.SRP,
        board_type=BoardType.RAINBOW,
        hero_in_position=True,
        hero_preflop_raiser=True,
        hero_pnl_bb=0.0,
        hero_preflop_invested_bb=2.0,
        pot_at_flop_bb=pot_at_flop_bb,
        flop_actions=flop_actions,
        hero_hand=hero_hand,
        villain_hand=villain_hand,
        flop_cards=flop_cards,
    )


RAINBOW_FLOP = [_c("T", "s"), _c("7", "h"), _c("3", "d")]


class TestEvNodeDataEmpty:
    """No events → sensible defaults."""

    def test_empty_events_returns_default_equity(self):
        store = LineEvents()
        result = store.ev_node_data(ALL_FILTER, [], None, None)

        assert result["hand_count"] == 0
        for triple in VALID_TRIPLES:
            assert result["equity_vs_full"][triple] == 0.5
            assert result["equity_vs_call"][triple] == 0.5
            assert result["equity_vs_raise"][triple] == 0.5

    def test_empty_events_reaction_counts_zero(self):
        store = LineEvents()
        result = store.ev_node_data(ALL_FILTER, [], None, None)

        assert result["fold_count"] == 0
        assert result["call_count"] == 0
        assert result["raise_count"] == 0
        assert result["median_raise_size_pct"] is None


class TestEvNodeDataKeys:
    """Structure and key validation."""

    def test_equity_dicts_have_all_valid_triples_as_keys(self):
        store = LineEvents()
        # Hero bets, villain calls with shown hand
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="C"),
            ],
            flop_cards=RAINBOW_FLOP,
            villain_hand=HoleCards(_c("Q", "c"), _c("J", "c")),
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)

        for key in ("equity_vs_full", "equity_vs_call", "equity_vs_raise"):
            assert set(result[key].keys()) == set(VALID_TRIPLES)

    def test_all_equities_between_zero_and_one(self):
        store = LineEvents()
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="C"),
            ],
            flop_cards=RAINBOW_FLOP,
            villain_hand=HoleCards(_c("Q", "c"), _c("J", "c")),
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)

        for key in ("equity_vs_full", "equity_vs_call", "equity_vs_raise"):
            for triple, equity in result[key].items():
                assert 0.0 <= equity <= 1.0, f"{key}[{triple}] = {equity}"


class TestEvNodeDataReactions:
    """Reaction counting logic."""

    def test_fold_counted(self):
        store = LineEvents()
        # Hero bets, villain folds
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="F"),
            ],
            flop_cards=RAINBOW_FLOP,
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)

        assert result["fold_count"] == 1
        assert result["call_count"] == 0
        assert result["raise_count"] == 0

    def test_call_counted(self):
        store = LineEvents()
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="C"),
            ],
            flop_cards=RAINBOW_FLOP,
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)

        assert result["fold_count"] == 0
        assert result["call_count"] == 1
        assert result["raise_count"] == 0

    def test_raise_counted_with_size(self):
        store = LineEvents()
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="R", size_pct=250.0),
            ],
            flop_cards=RAINBOW_FLOP,
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)

        assert result["raise_count"] == 1
        assert result["median_raise_size_pct"] == 250.0

    def test_mixed_reactions(self):
        store = LineEvents()
        # 2 folds, 3 calls, 1 raise
        for _ in range(2):
            store.add_event(_make_event(
                flop_actions=[
                    StreetAction(actor="hero", action="B", size_pct=50.0),
                    StreetAction(actor="villain", action="F"),
                ],
                flop_cards=RAINBOW_FLOP,
            ))
        for _ in range(3):
            store.add_event(_make_event(
                flop_actions=[
                    StreetAction(actor="hero", action="B", size_pct=50.0),
                    StreetAction(actor="villain", action="C"),
                ],
                flop_cards=RAINBOW_FLOP,
            ))
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="R", size_pct=300.0),
            ],
            flop_cards=RAINBOW_FLOP,
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)

        assert result["fold_count"] == 2
        assert result["call_count"] == 3
        assert result["raise_count"] == 1
        assert result["hand_count"] == 6


class TestEvNodeDataEquity:
    """Equity accuracy tests."""

    def test_stronger_hero_has_higher_equity(self):
        """SET should have higher equity_vs_full than PAIR vs same villain."""
        store = LineEvents()
        # Villain has top pair (Ts on T-7-3 board)
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="C"),
            ],
            flop_cards=RAINBOW_FLOP,
            villain_hand=HoleCards(_c("T", "c"), _c("9", "c")),
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)

        set_triple = (MadeHandType.SET, FlushDrawType.NONE, StraightDrawType.NONE)
        pair_triple = (MadeHandType.PAIR, FlushDrawType.NONE, StraightDrawType.NONE)

        assert result["equity_vs_full"][set_triple] > result["equity_vs_full"][pair_triple]

    def test_no_villain_hands_shown_gives_default_equity(self):
        """When villain never shows, all equities are 0.5 but reaction counts still work."""
        store = LineEvents()
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="F"),
            ],
            flop_cards=RAINBOW_FLOP,
            villain_hand=None,
        ))
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="C"),
            ],
            flop_cards=RAINBOW_FLOP,
            villain_hand=None,
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)

        assert result["fold_count"] == 1
        assert result["call_count"] == 1
        for triple in VALID_TRIPLES:
            assert result["equity_vs_full"][triple] == 0.5


class TestEvNodeDataMedianRaise:
    """Median raise size calculation."""

    def test_single_raise(self):
        store = LineEvents()
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="R", size_pct=200.0),
            ],
            flop_cards=RAINBOW_FLOP,
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)
        assert result["median_raise_size_pct"] == 200.0

    def test_multiple_raises_odd_count(self):
        store = LineEvents()
        for size in [150.0, 250.0, 300.0]:
            store.add_event(_make_event(
                flop_actions=[
                    StreetAction(actor="hero", action="B", size_pct=50.0),
                    StreetAction(actor="villain", action="R", size_pct=size),
                ],
                flop_cards=RAINBOW_FLOP,
            ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)
        assert result["median_raise_size_pct"] == 250.0

    def test_no_raises_gives_none(self):
        store = LineEvents()
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="C"),
            ],
            flop_cards=RAINBOW_FLOP,
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)
        assert result["median_raise_size_pct"] is None


class TestEvNodeDataPotAndMeta:
    """Pot size and metadata."""

    def test_pot_bb_uses_correct_street_field(self):
        store = LineEvents()
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="C"),
            ],
            flop_cards=RAINBOW_FLOP,
            pot_at_flop_bb=8.5,
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)
        assert result["pot_bb"] == 8.5
        assert result["street"] == "flop"

    def test_next_actor_is_hero(self):
        store = LineEvents()
        store.add_event(_make_event(
            flop_actions=[
                StreetAction(actor="hero", action="B", size_pct=50.0),
                StreetAction(actor="villain", action="C"),
            ],
            flop_cards=RAINBOW_FLOP,
        ))
        result = store.ev_node_data(ALL_FILTER, [], None, None)
        assert result["next_actor"] == "hero"
