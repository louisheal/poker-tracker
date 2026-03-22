from enum import Enum


class BoardType(Enum):
	MONOTONE = 0
	TWO_TONE = 1
	RAINBOW = 2


class PotType(str, Enum):
	SRP = "SRP"
	THREE_BET = "THREE_BET"
	FOUR_BET = "FOUR_BET"


class ActionSequence(str, Enum):
	XX = "XX"
	XBC = "XBC"
	XBRC = "XBRC"
	BC = "BC"


class Runout(str, Enum):
	OVERCARD = "OVERCARD"
	FLUSH_COMPLETING = "FLUSH_COMPLETING"
	PAIRED = "PAIRED"
	OTHER = "OTHER"


class FlopRankTexture(str, Enum):
	TRIPS = "TRIPS"
	PAIRED = "PAIRED"
	UNPAIRED = "UNPAIRED"


class ShowdownType(str, Enum):
	CHECK_CHECK = "CHECK_CHECK"
	BET_CALL = "BET_CALL"
	RAISE_OCCURRED = "RAISE_OCCURRED"
