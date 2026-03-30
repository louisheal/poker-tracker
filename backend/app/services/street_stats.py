"""Service layer for street stats panel -- orchestrates DB queries."""
from __future__ import annotations

import sqlite3

from app.db.queries import query_node_action_counts


NODE_SUFFIXES = ["", "_B", "_B_R", "_X", "_X_B", "_X_B_R"]


def get_street_stats(
	conn: sqlite3.Connection,
	base_key: str,
	**filters,
) -> dict:
	"""Query all 6 node_keys for a street and return action counts per node."""
	results = {}
	for suffix in NODE_SUFFIXES:
		node_key = f"{base_key}{suffix}"
		results[node_key] = query_node_action_counts(conn, node_key, **filters)
	return results


def build_base_key(
	flop_sequence: str = "",
	turn_sequence: str | None = None,
	river_sequence: str | None = None,
) -> str:
	"""Build the base node_key from per-street action sequences.

	Examples:
	  ("", None, None)             -> "FLOP"
	  ("X_B_C", "", None)          -> "FLOP_X_B_C_TURN"
	  ("B_C", "X_B_C", "")        -> "FLOP_B_C_TURN_X_B_C_RIVER"
	"""
	key = "FLOP"
	if flop_sequence:
		key = f"{key}_{flop_sequence}"
	if turn_sequence is not None:
		key = f"{key}_TURN"
		if turn_sequence:
			key = f"{key}_{turn_sequence}"
	if river_sequence is not None:
		key = f"{key}_RIVER"
		if river_sequence:
			key = f"{key}_{river_sequence}"
	return key
