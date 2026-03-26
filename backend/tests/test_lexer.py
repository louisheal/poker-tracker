"""Tests for the hand history lexer."""

import pytest

from app.parsers.lexer import lex_hand
from app.parsers.core import flop_player_count


HAND_WITH_SPACED_NAMES = [
    "Poker Hand #RC3171144742: Hold'em No Limit ($0.01/$0.02) - 2024/12/23 00:10:21",
    "Table 'RushAndCash6869970' 6-max Seat #1 is the button",
    "Seat 1: Jazz star ($2.79 in chips)",
    "Seat 2: rafa8723 ($2.01 in chips)",
    "Seat 3: llHavokll ($3.37 in chips)",
    "Seat 4: frozzorw0w ($5.73 in chips)",
    "Seat 5: Spissatus ($1.31 in chips)",
    "Seat 6: Kingslayer185 ($1.06 in chips)",
    "rafa8723: posts small blind $0.01",
    "llHavokll: posts big blind $0.02",
    "*** HOLE CARDS ***",
    "Dealt to Jazz star",
    "Dealt to rafa8723",
    "Dealt to llHavokll",
    "Dealt to frozzorw0w",
    "Dealt to Spissatus",
    "Dealt to Kingslayer185",
    "frozzorw0w: raises $0.02 to $0.04",
    "Spissatus: folds",
    "Kingslayer185: folds",
    "Jazz star: folds",
    "rafa8723: calls $0.03",
    "llHavokll: folds",
    "*** FLOP *** [4c Ad 9s]",
    "rafa8723: checks",
    "frozzorw0w: bets $0.03",
    "rafa8723: calls $0.03",
    "*** TURN *** [4c Ad 9s] [9h]",
    "rafa8723: checks",
    "frozzorw0w: bets $0.05",
    "rafa8723: calls $0.05",
    "*** RIVER *** [4c Ad 9s 9h] [6h]",
    "rafa8723: checks",
    "frozzorw0w: bets $0.20",
    "rafa8723: folds",
    "Uncalled bet ($0.20) returned to frozzorw0w",
    "*** SHOWDOWN ***",
    "frozzorw0w collected $0.25 from pot",
    "*** SUMMARY ***",
    "Total pot $0.26 | Rake $0.01 | Jackpot $0.00 | Bingo $0 | Fortune $0 | Tax $0",
    "Board [4c Ad 9s 9h 6h]",
    "Seat 1: Jazz star (button) folded before Flop (didn't bet)",
    "Seat 2: rafa8723 (small blind) folded on the River",
    "Seat 3: llHavokll (big blind) folded before Flop (didn't bet)",
    "Seat 4: frozzorw0w won ($0.25)",
    "Seat 5: Spissatus folded before Flop (didn't bet)",
    "Seat 6: Kingslayer185 folded before Flop (didn't bet)",
]

HAND_WITH_SHOWDOWN_SPACED_NAMES = [
    "Poker Hand #RC9999999999: Hold'em No Limit ($0.01/$0.02) - 2024/12/23 01:00:00",
    "Table 'RushAndCash1234567' 6-max Seat #3 is the button",
    "Seat 1: Dr Omaha7 ($5.95 in chips)",
    "Seat 2: Chandler B!ng ($2.02 in chips)",
    "Seat 3: Jazz star ($2.79 in chips)",
    "Seat 4: rafa8723 ($2.01 in chips)",
    "Seat 5: Spissatus ($1.31 in chips)",
    "Seat 6: Kingslayer185 ($1.06 in chips)",
    "rafa8723: posts small blind $0.01",
    "Spissatus: posts big blind $0.02",
    "*** HOLE CARDS ***",
    "Dealt to Dr Omaha7",
    "Dealt to Chandler B!ng",
    "Dealt to Jazz star",
    "Dealt to rafa8723",
    "Dealt to Spissatus",
    "Dealt to Kingslayer185",
    "Kingslayer185: folds",
    "Dr Omaha7: raises $0.04 to $0.06",
    "Chandler B!ng: calls $0.06",
    "Jazz star: folds",
    "rafa8723: folds",
    "Spissatus: folds",
    "*** FLOP *** [Qh 3d Kc]",
    "Dr Omaha7: bets $0.07",
    "Chandler B!ng: calls $0.07",
    "*** TURN *** [Qh 3d Kc] [5h]",
    "Dr Omaha7: bets $0.15",
    "Chandler B!ng: calls $0.15",
    "*** RIVER *** [Qh 3d Kc 5h] [7c]",
    "Dr Omaha7: checks",
    "Chandler B!ng: bets $0.30",
    "Dr Omaha7: calls $0.30",
    "*** SHOWDOWN ***",
    "Chandler B!ng: shows [Ah Kh]",
    "Dr Omaha7: shows [Ks Qd]",
    "Dr Omaha7 collected $1.14 from pot",
    "*** SUMMARY ***",
    "Total pot $1.19 | Rake $0.05 | Jackpot $0.00 | Bingo $0 | Fortune $0 | Tax $0",
    "Board [Qh 3d Kc 5h 7c]",
    "Seat 1: Dr Omaha7 collected ($1.14)",
    "Seat 2: Chandler B!ng showed [Ah Kh] and lost",
    "Seat 3: Jazz star (button) folded before Flop (didn't bet)",
    "Seat 4: rafa8723 (small blind) folded before Flop (didn't bet)",
    "Seat 5: Spissatus (big blind) folded before Flop (didn't bet)",
    "Seat 6: Kingslayer185 folded before Flop (didn't bet)",
]


class TestLexerSpacedPlayerNames:
    """Verify the lexer handles player names containing spaces."""

    def test_parses_hand_with_spaced_name_in_seat(self):
        ast = lex_hand(HAND_WITH_SPACED_NAMES)
        assert ast is not None
        player_names = [name for name, _, _ in ast.players]
        assert "Jazz star" in player_names

    def test_all_six_players_parsed(self):
        ast = lex_hand(HAND_WITH_SPACED_NAMES)
        assert ast is not None
        assert len(ast.players) == 6

    def test_stacks_correct_for_spaced_name(self):
        ast = lex_hand(HAND_WITH_SPACED_NAMES)
        assert ast is not None
        jazz_star = next((name, seat, stack) for name, seat, stack in ast.players if name == "Jazz star")
        assert jazz_star == ("Jazz star", 1, 2.79)

    def test_no_hero_hole_cards(self):
        ast = lex_hand(HAND_WITH_SPACED_NAMES)
        assert ast is not None
        assert ast.hero_hole_cards is None

    def test_preflop_actions_include_spaced_name(self):
        ast = lex_hand(HAND_WITH_SPACED_NAMES)
        assert ast is not None
        fold_players = [a.player for a in ast.preflop if a.type.value == "fold"]
        assert "Jazz star" in fold_players

    def test_flop_turn_river_parsed(self):
        ast = lex_hand(HAND_WITH_SPACED_NAMES)
        assert ast is not None
        assert ast.flop is not None
        assert len(ast.flop.cards) == 3
        assert ast.turn is not None
        assert ast.river is not None

    def test_collections_correct(self):
        ast = lex_hand(HAND_WITH_SPACED_NAMES)
        assert ast is not None
        assert ast.collections.get("frozzorw0w") == 0.25

    def test_total_pot(self):
        ast = lex_hand(HAND_WITH_SPACED_NAMES)
        assert ast is not None
        assert ast.total_pot == 0.26

    def test_uncalled_bet(self):
        ast = lex_hand(HAND_WITH_SPACED_NAMES)
        assert ast is not None
        assert ast.uncalled_amount == 0.20
        assert ast.uncalled_to == "frozzorw0w"


class TestLexerShowdownSpacedNames:
    """Verify shows and collected work with spaced player names."""

    def test_shown_cards_spaced_names(self):
        ast = lex_hand(HAND_WITH_SHOWDOWN_SPACED_NAMES)
        assert ast is not None
        assert "Chandler B!ng" in ast.shown_cards
        assert "Dr Omaha7" in ast.shown_cards

    def test_showdown_collection_spaced_name(self):
        ast = lex_hand(HAND_WITH_SHOWDOWN_SPACED_NAMES)
        assert ast is not None
        assert ast.collections.get("Dr Omaha7") == 1.14

    def test_summary_collected_spaced_name(self):
        ast = lex_hand(HAND_WITH_SHOWDOWN_SPACED_NAMES)
        assert ast is not None
        assert ast.collections.get("Dr Omaha7") == 1.14

    def test_all_flop_actions_parsed(self):
        ast = lex_hand(HAND_WITH_SHOWDOWN_SPACED_NAMES)
        assert ast is not None
        assert ast.flop is not None
        flop_players = [a.player for a in ast.flop.actions]
        assert "Dr Omaha7" in flop_players
        assert "Chandler B!ng" in flop_players


class TestFlopPlayerCountSpacedNames:
    """Verify flop_player_count handles spaced names correctly."""

    def test_counts_two_players_at_flop(self):
        count = flop_player_count(HAND_WITH_SPACED_NAMES)
        assert count == 2

    def test_counts_two_players_showdown_hand(self):
        count = flop_player_count(HAND_WITH_SHOWDOWN_SPACED_NAMES)
        assert count == 2
