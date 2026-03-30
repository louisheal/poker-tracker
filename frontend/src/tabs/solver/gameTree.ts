import type {
  ActionTile,
  Tile,
  SolverSpot,
  Position,
  ActionOption,
} from "./types";
import {
  POSITIONS,
  POSTFLOP_POSITION_ORDER,
  PREFLOP_ACTIONS,
  PREFLOP_BB_CHECK_ACTIONS,
  POSTFLOP_OPEN_ACTIONS,
  POSTFLOP_FACING_BET_ACTIONS,
} from "./types";

/**
 * Determine postflop acting order from the two active players.
 * Returns [OOP, IP] where OOP acts first.
 */
export function getPostflopOrder(
  activePlayers: Position[],
): [Position, Position] | null {
  const sorted = POSTFLOP_POSITION_ORDER.filter((p) =>
    activePlayers.includes(p),
  );
  if (sorted.length !== 2) return null;
  return [sorted[0], sorted[1]];
}

/**
 * Given existing street actions, determine the next player to act
 * and their available options. Returns null if the street is complete.
 */
function getPostflopNext(
  streetActions: string[],
): { player: "oop" | "ip"; options: ActionOption[] } | null {
  const n = streetActions.length;

  if (n === 0) {
    return { player: "oop", options: POSTFLOP_OPEN_ACTIONS };
  }

  const lastAction = streetActions[n - 1];

  if (lastAction === "Fold") return null;
  if (lastAction === "Call") return null;
  if (
    lastAction === "Check" &&
    n >= 2 &&
    streetActions[n - 2] === "Check"
  ) {
    return null;
  }

  const nextPlayer: "oop" | "ip" = n % 2 === 0 ? "oop" : "ip";

  if (lastAction === "Check") {
    return { player: nextPlayer, options: POSTFLOP_OPEN_ACTIONS };
  }

  return { player: nextPlayer, options: POSTFLOP_FACING_BET_ACTIONS };
}

/**
 * Build the full tile sequence from the current solver spot state.
 */
export function buildTiles(spot: SolverSpot): Tile[] {
  const tiles: Tile[] = [];

  const preflopResult = buildPreflopTiles(spot.preflopActions);
  tiles.push(...preflopResult.tiles);

  if (!preflopResult.complete) return tiles;
  if (preflopResult.activePlayers.length !== 2) return tiles;

  const postflopOrder = getPostflopOrder(preflopResult.activePlayers);
  if (!postflopOrder) return tiles;
  const [oopPos, ipPos] = postflopOrder;

  const flopBoardComplete = spot.flopCards.length >= 3;
  tiles.push({
    type: "board",
    id: "flop-board",
    street: "flop",
    requiredCards: 3,
    cards: spot.flopCards,
    complete: flopBoardComplete,
  });
  if (!flopBoardComplete) return tiles;

  const flopResult = buildPostflopTiles(
    "flop",
    spot.flopActions,
    oopPos,
    ipPos,
  );
  tiles.push(...flopResult.tiles);
  if (!flopResult.complete || flopResult.handOver) return tiles;

  const turnBoardComplete = spot.turnCard !== null;
  tiles.push({
    type: "board",
    id: "turn-board",
    street: "turn",
    requiredCards: 1,
    cards: spot.turnCard ? [spot.turnCard] : [],
    complete: turnBoardComplete,
  });
  if (!turnBoardComplete) return tiles;

  const turnResult = buildPostflopTiles(
    "turn",
    spot.turnActions,
    oopPos,
    ipPos,
  );
  tiles.push(...turnResult.tiles);
  if (!turnResult.complete || turnResult.handOver) return tiles;

  const riverBoardComplete = spot.riverCard !== null;
  tiles.push({
    type: "board",
    id: "river-board",
    street: "river",
    requiredCards: 1,
    cards: spot.riverCard ? [spot.riverCard] : [],
    complete: riverBoardComplete,
  });
  if (!riverBoardComplete) return tiles;

  const riverResult = buildPostflopTiles(
    "river",
    spot.riverActions,
    oopPos,
    ipPos,
  );
  tiles.push(...riverResult.tiles);

  return tiles;
}

/**
 * Get the active players after preflop is resolved.
 * Useful for SolverView to determine IP/OOP labels.
 */
export function getPreflopActivePlayers(
  preflopActions: string[],
): { complete: boolean; activePlayers: Position[] } {
  const result = buildPreflopTiles(preflopActions);
  return { complete: result.complete, activePlayers: result.activePlayers };
}

// ---------------------------------------------------------------------------
// Preflop tile generation
// ---------------------------------------------------------------------------

function buildPreflopTiles(preflopActions: string[]): {
  tiles: ActionTile[];
  complete: boolean;
  activePlayers: Position[];
} {
  const tiles: ActionTile[] = [];
  const active = new Set<Position>([...POSITIONS]);
  let raiseCount = 0;
  let lastRaiser: Position | null = null;
  let actedSinceLastRaise = new Set<Position>();
  let actionIndex = 0;

  const toAct: Position[] = [...POSITIONS];

  function allActedSinceRaise(): boolean {
    if (!lastRaiser) return false;
    for (const p of active) {
      if (p !== lastRaiser && !actedSinceLastRaise.has(p)) return false;
    }
    return true;
  }

  for (let qi = 0; qi < toAct.length; qi++) {
    const pos = toAct[qi];
    if (!active.has(pos)) continue;

    // The last raiser doesn't act again unless re-raised
    if (pos === lastRaiser) continue;

    // Already acted since the last raise (stale queue entry)
    if (actedSinceLastRaise.has(pos)) continue;

    const isBBNoRaise = pos === "BB" && raiseCount === 0;
    const options = isBBNoRaise ? PREFLOP_BB_CHECK_ACTIONS : PREFLOP_ACTIONS;

    const selected =
      actionIndex < preflopActions.length
        ? preflopActions[actionIndex]
        : null;

    tiles.push({
      type: "action",
      id: `preflop-${tiles.length}`,
      label: pos,
      options,
      selected,
      section: "preflop",
      actionIndex,
    });

    if (selected === null) {
      return { tiles, complete: false, activePlayers: [...active] };
    }

    actionIndex++;
    actedSinceLastRaise.add(pos);

    if (selected === "Fold") {
      active.delete(pos);
      actedSinceLastRaise.delete(pos);
      if (active.size <= 1) {
        return { tiles, complete: true, activePlayers: [...active] };
      }
    } else if (selected === "Raise") {
      raiseCount++;
      lastRaiser = pos;
      actedSinceLastRaise = new Set([pos]);
      for (const p of POSITIONS) {
        if (active.has(p) && p !== pos) {
          toAct.push(p);
        }
      }
    }

    if (lastRaiser && allActedSinceRaise()) break;
  }

  return { tiles, complete: true, activePlayers: [...active] };
}

// ---------------------------------------------------------------------------
// Postflop tile generation
// ---------------------------------------------------------------------------

function buildPostflopTiles(
  street: "flop" | "turn" | "river",
  streetActions: string[],
  oopPos: Position,
  ipPos: Position,
): {
  tiles: ActionTile[];
  complete: boolean;
  handOver: boolean;
} {
  const tiles: ActionTile[] = [];

  for (let i = 0; ; i++) {
    const actionsToThisPoint = streetActions.slice(0, i);
    const next = getPostflopNext(actionsToThisPoint);

    if (next === null) {
      const handOver = i > 0 && streetActions[i - 1] === "Fold";
      return { tiles, complete: true, handOver };
    }

    const pos = next.player === "oop" ? oopPos : ipPos;
    const selected = i < streetActions.length ? streetActions[i] : null;

    tiles.push({
      type: "action",
      id: `${street}-${i}`,
      label: next.player.toUpperCase(),
      sublabel: pos,
      options: next.options,
      selected,
      section: street,
      actionIndex: i,
    });

    if (selected === null) {
      return { tiles, complete: false, handOver: false };
    }
  }
}
