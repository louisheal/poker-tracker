import logging
import re
from datetime import date, datetime

from playing_cards_lib.core import Card, Rank, Suit
from playing_cards_lib.poker import HoleCards

logger = logging.getLogger(__name__)

START_RE = re.compile(r"^Poker Hand #[^:]+: .* - (\d{4}/\d{2}/\d{2}) \d{2}:\d{2}:\d{2}$")
DEALT_HERO_RE = re.compile(r"Dealt to\s+Hero\s*\[([2-9TJQKA][shdc])\s+([2-9TJQKA][shdc])\]", re.IGNORECASE)
ACTION_RE = re.compile(r"(.*): (folds|calls|raises|checks|bets)\b", re.IGNORECASE)
SUMMARY_RE = re.compile(r"^\*\*\*\s*SUMMARY\s*\*\*\*")
FLOP_RE = re.compile(r"\*\*\* FLOP \*\*\* \[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\]", re.IGNORECASE)
TURN_RE = re.compile(r"\*\*\* TURN \*\*\* \[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\] \[([2-9TJQKA][shdc])\]", re.IGNORECASE)
RIVER_RE = re.compile(r"\*\*\* RIVER \*\*\* \[([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc]) ([2-9TJQKA][shdc])\] \[([2-9TJQKA][shdc])\]", re.IGNORECASE)
TOTAL_POT_RE = re.compile(r"Total pot \$(\d+\.?\d*)")
HERO_SHOWDOWN_RE = re.compile(r"Hero.*showed.*and (won|lost)")
SEAT_RE = re.compile(r"^Seat\s+\d+:\s+([^\s]+)")
BLIND_RE = re.compile(r"posts (?:small|big) blind \$(\d+\.?\d*)")
BET_AMOUNT_RE = re.compile(r": bets \$(\d+\.?\d*)")
CALL_AMOUNT_RE = re.compile(r": calls \$(\d+\.?\d*)")
RAISE_TO_AMOUNT_RE = re.compile(r": raises \$[\d.]+ to \$(\d+\.?\d*)")
UNCALLED_RE = re.compile(r"Uncalled bet \(\$(\d+\.?\d*)\)")
HERO_COLLECTED_RE = re.compile(r"Hero collected \$(\d+\.?\d*)")
HERO_WON_RE = re.compile(r"Hero.*and won \(\$(\d+\.?\d*)\)")
RAISE_INC_RE = re.compile(r": raises \$(\d+\.?\d*) to \$(\d+\.?\d*)")

def to_card(token: str) -> Card:
	t = token.strip()
	rank_token = t[0].upper()
	suit_token = t[1].upper()
	rank = Rank(rank_token)
	suit = Suit(suit_token)
	return Card(rank, suit)

def to_hole_cards(fst: str, snd: str) -> HoleCards:
	fst_card = to_card(fst)
	snd_card = to_card(snd)
	return HoleCards(fst_card, snd_card)


def parse_hand_date(lines: list[str]) -> date | None:
	for line in lines:
		m = START_RE.search(line)
		if not m:
			continue
		return datetime.strptime(m.group(1), "%Y/%m/%d").date()
	return None


def flop_player_count(lines: list[str]) -> int | None:
	players: set[str] = set()
	for line in lines:
		seat = SEAT_RE.search(line)
		if seat:
			players.add(seat.group(1))

	active_players = set(players)
	for line in lines:
		if FLOP_RE.search(line):
			return len(active_players)
		action = ACTION_RE.search(line)
		if not action:
			continue
		if action.group(2).lower() == "folds":
			active_players.discard(action.group(1))
	return None

def group_hands(file, include_multiway: bool = False):
	curr_hand = []

	with open(file, 'r', encoding='utf-8') as f:
		for line in f:
			text = line.strip()
			if not text:
				if curr_hand:
					if include_multiway:
						yield curr_hand
					else:
						players_on_flop = flop_player_count(curr_hand)
						if players_on_flop is None or players_on_flop <= 2:
							yield curr_hand
					curr_hand = []
				continue

			if "Poker Hand" in text and curr_hand:
				if include_multiway:
					yield curr_hand
				else:
					players_on_flop = flop_player_count(curr_hand)
					if players_on_flop is None or players_on_flop <= 2:
						yield curr_hand
				curr_hand = []

			curr_hand.append(text)

	if curr_hand:
		if include_multiway:
			yield curr_hand
		else:
			players_on_flop = flop_player_count(curr_hand)
			if players_on_flop is None or players_on_flop <= 2:
				yield curr_hand
