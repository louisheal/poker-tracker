from app.parsers.hand_types import classify_flush_draw, classify_straight_draw
from app.models.enums import FlushDrawType, StraightDrawType
from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards


def _c(rank_str, suit_str):
    rank_map = {"2": Rank.TWO, "3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
                "6": Rank.SIX, "7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE,
                "T": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN, "K": Rank.KING, "A": Rank.ACE}
    suit_map = {"h": Suit.HEARTS, "d": Suit.DIAMONDS, "s": Suit.SPADES, "c": Suit.CLUBS}
    return Card(rank_map[rank_str], suit_map[suit_str])


class TestClassifyFlushDraw:

    def test_front_door_flush_draw(self):
        hole = HoleCards(_c("A", "h"), _c("K", "h"))
        board = [_c("7", "h"), _c("3", "h"), _c("9", "s")]
        assert classify_flush_draw(hole, board) == FlushDrawType.FRONT_DOOR

    def test_backdoor_flush_draw_on_flop(self):
        hole = HoleCards(_c("A", "h"), _c("K", "h"))
        board = [_c("7", "h"), _c("3", "s"), _c("9", "d")]
        assert classify_flush_draw(hole, board) == FlushDrawType.BACK_DOOR

    def test_no_flush_draw(self):
        hole = HoleCards(_c("A", "h"), _c("K", "d"))
        board = [_c("7", "s"), _c("3", "c"), _c("9", "s")]
        assert classify_flush_draw(hole, board) == FlushDrawType.NONE

    def test_river_always_none(self):
        hole = HoleCards(_c("A", "h"), _c("K", "h"))
        board = [_c("7", "h"), _c("3", "h"), _c("9", "s"), _c("T", "d"), _c("2", "c")]
        assert classify_flush_draw(hole, board) == FlushDrawType.NONE

    def test_already_a_flush_is_none(self):
        hole = HoleCards(_c("A", "h"), _c("K", "h"))
        board = [_c("7", "h"), _c("3", "h"), _c("9", "h")]
        assert classify_flush_draw(hole, board) == FlushDrawType.NONE

    def test_hero_must_contribute(self):
        hole = HoleCards(_c("A", "d"), _c("K", "c"))
        board = [_c("7", "h"), _c("3", "h"), _c("9", "h"), _c("T", "h")]
        assert classify_flush_draw(hole, board) == FlushDrawType.NONE


class TestClassifyStraightDraw:

    def test_oesd(self):
        hole = HoleCards(_c("J", "h"), _c("T", "d"))
        board = [_c("9", "s"), _c("8", "c"), _c("2", "h")]
        assert classify_straight_draw(hole, board) == StraightDrawType.OESD

    def test_gutshot(self):
        hole = HoleCards(_c("J", "h"), _c("T", "d"))
        board = [_c("9", "s"), _c("7", "c"), _c("2", "h")]
        assert classify_straight_draw(hole, board) == StraightDrawType.GUTSHOT

    def test_no_straight_draw(self):
        hole = HoleCards(_c("A", "h"), _c("2", "d"))
        board = [_c("K", "s"), _c("9", "c"), _c("5", "h")]
        assert classify_straight_draw(hole, board) == StraightDrawType.NONE

    def test_river_always_none(self):
        hole = HoleCards(_c("J", "h"), _c("T", "d"))
        board = [_c("9", "s"), _c("8", "c"), _c("2", "h"), _c("3", "d"), _c("4", "c")]
        assert classify_straight_draw(hole, board) == StraightDrawType.NONE
