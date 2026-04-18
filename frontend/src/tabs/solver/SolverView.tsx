import { useState, useMemo, useCallback } from "react";
import type { CardJson } from "@/api";
import type { SolverSpot, ActionTile, BoardTile } from "./types";
import { INITIAL_SPOT, ALL_IN_OPTION } from "./types";
import { buildTiles } from "./gameTree";
import { ActionSequence } from "./components/ActionSequence";
import { HandGrid } from "./components/HandGrid";
import { SolverResults } from "./components/SolverResults";
import { DebugPanels } from "./components/DebugPanels";
import { useSolverStream } from "./hooks/useSolverStream";

export const SolverView = () => {
  const [spot, setSpot] = useState<SolverSpot>(INITIAL_SPOT);
  const [viewTileId, setViewTileId] = useState<string | null>(null);
  const [selectedHand, setSelectedHand] = useState<string | null>(null);

  const tiles = useMemo(() => buildTiles(spot), [spot]);

  // The first pending tile (for auto-cursor)
  const firstPendingTileId = tiles.find((t) => {
    if (t.type === "action") return t.selected === null;
    if (t.type === "board") return !t.complete;
    return false;
  })?.id ?? null;

  // Resolve the viewed tile: use explicit cursor, or fall back to first pending
  const effectiveViewId = viewTileId ?? firstPendingTileId;
  const viewedTile = tiles.find((t) => t.id === effectiveViewId) ?? null;

  // The base action options for the viewed decision point (before solver filtering)
  const tileActionOptions = useMemo(() => {
    if (viewedTile?.type === "action") return viewedTile.options;
    return [];
  }, [viewedTile]);

  // All board cards for disabling in card pickers
  const allBoardCards = useMemo(
    () => [
      ...spot.flopCards,
      ...(spot.turnCard ? [spot.turnCard] : []),
      ...(spot.riverCard ? [spot.riverCard] : []),
    ],
    [spot.flopCards, spot.turnCard, spot.riverCard],
  );

  // Build solver params based on the viewed tile
  const solverParams = useMemo(() => {
    if (!viewedTile || viewedTile.type !== "action") return null;
    const actions: string[] = [];
    for (const t of tiles) {
      if (t === viewedTile) break;
      if (t.type === "action" && t.selected !== null) {
        actions.push(`${t.label}:${t.selected}`);
      }
    }

    // Only include board cards up to the viewed tile's street
    const street = viewedTile.section;
    const boardCards: CardJson[] = [];
    if (street === "flop" || street === "turn" || street === "river") {
      boardCards.push(...spot.flopCards);
    }
    if (street === "turn" || street === "river") {
      if (spot.turnCard) boardCards.push(spot.turnCard);
    }
    if (street === "river") {
      if (spot.riverCard) boardCards.push(spot.riverCard);
    }
    const board = boardCards.map(
      (c) => `${c.Rank}${c.Suit.toLowerCase()}`,
    );

    const heroPosition = viewedTile.sublabel ?? viewedTile.label;
    return {
      board,
      street,
      actions,
      heroPosition,
    };
  }, [viewedTile, tiles, spot.flopCards, spot.turnCard, spot.riverCard]);

  const { result: solverResult, loading, progress, simsComplete } =
    useSolverStream(solverParams);

  // Filter action options to only those the solver returned, inject All-in
  const viewedActionOptions = useMemo(() => {
    if (!solverResult?.actions) return tileActionOptions;
    const solverKeys = new Set(Object.keys(solverResult.actions));
    const filtered = tileActionOptions.filter((opt) => solverKeys.has(opt.key));
    if (solverKeys.has("All-in") && !filtered.some((opt) => opt.key === "All-in")) {
      filtered.push(ALL_IN_OPTION);
    }
    return filtered;
  }, [tileActionOptions, solverResult]);

  const handleNavigate= useCallback((tileId: string) => {
    setViewTileId(tileId);
    setSelectedHand(null);
  }, []);

  const handleActionSelect = useCallback(
    (tileId: string, action: string) => {
      const tile = tiles.find((t) => t.id === tileId) as ActionTile;
      if (!tile) return;

      // If the action is the same as already selected, just navigate
      if (tile.selected === action) {
        setViewTileId(tileId);
        return;
      }

      setSpot((prev) => {
        const next = { ...prev };

        if (tile.section === "preflop") {
          const updated = [...prev.preflopActions];
          updated[tile.actionIndex] = action;
          next.preflopActions = updated.slice(0, tile.actionIndex + 1);
          next.flopCards = [];
          next.flopActions = [];
          next.turnCard = null;
          next.turnActions = [];
          next.riverCard = null;
          next.riverActions = [];
        } else if (tile.section === "flop") {
          const updated = [...prev.flopActions];
          updated[tile.actionIndex] = action;
          next.flopActions = updated.slice(0, tile.actionIndex + 1);
          next.turnCard = null;
          next.turnActions = [];
          next.riverCard = null;
          next.riverActions = [];
        } else if (tile.section === "turn") {
          const updated = [...prev.turnActions];
          updated[tile.actionIndex] = action;
          next.turnActions = updated.slice(0, tile.actionIndex + 1);
          next.riverCard = null;
          next.riverActions = [];
        } else if (tile.section === "river") {
          const updated = [...prev.riverActions];
          updated[tile.actionIndex] = action;
          next.riverActions = updated.slice(0, tile.actionIndex + 1);
        }

        return next;
      });

      // Reset cursor to auto (will land on next pending tile)
      setViewTileId(null);
    },
    [tiles],
  );

  const handleBoardChange = useCallback(
    (tileId: string, cards: CardJson[]) => {
      const tile = tiles.find((t) => t.id === tileId) as BoardTile;
      if (!tile) return;

      setSpot((prev) => {
        const next = { ...prev };

        if (tile.street === "flop") {
          next.flopCards = cards;
          next.flopActions = [];
          next.turnCard = null;
          next.turnActions = [];
          next.riverCard = null;
          next.riverActions = [];
        } else if (tile.street === "turn") {
          next.turnCard = cards[0] ?? null;
          next.turnActions = [];
          next.riverCard = null;
          next.riverActions = [];
        } else if (tile.street === "river") {
          next.riverCard = cards[0] ?? null;
          next.riverActions = [];
        }

        return next;
      });

      setViewTileId(null);
    },
    [tiles],
  );

  const hasDecisionPoint =
    viewedTile?.type === "action" && viewedActionOptions.length > 0;

  // Check if preflop ended with all folds
  const preflopComplete = tiles.some(
    (t) => t.type === "board" && t.street === "flop",
  );
  const allFolded =
    !preflopComplete &&
    tiles.length > 0 &&
    tiles.every((t) => t.type === "action" && t.selected !== null);

  return (
    <div className="flex flex-col gap-4 p-6">
      {/* Header */}
      <div>
        <h1 className="text-lg font-semibold text-foreground">Solver</h1>
        <p className="text-xs text-muted-foreground mt-1">
          Build a preflop action sequence, then enter the board to explore
          postflop strategy
        </p>
      </div>

      {/* Action Sequence */}
      <ActionSequence
        tiles={tiles}
        viewTileId={effectiveViewId}
        allBoardCards={allBoardCards}
        onActionSelect={handleActionSelect}
        onBoardChange={handleBoardChange}
        onNavigate={handleNavigate}
      />

      {/* Status messages */}
      {allFolded && !preflopComplete && (
        <div className="text-sm text-muted-foreground py-6 text-center">
          All players folded. Adjust the preflop sequence to get a heads-up pot.
        </div>
      )}

      {loading && (
        <div className="py-4">
          <div className="w-full bg-muted rounded h-2 overflow-hidden">
            <div
              className="bg-blue-500 h-2 rounded transition-all duration-300"
              style={{ width: `${Math.max(progress * 100, 2)}%` }}
            />
          </div>
          <span className="text-xs text-muted-foreground mt-1 block">
            {simsComplete > 0
              ? `${simsComplete} cards enumerated...`
              : "Solving..."}
          </span>
        </div>
      )}

      {/* Results */}
      {solverResult && hasDecisionPoint && (
        <div className="flex gap-6 items-start">
          <div className="flex-1 min-w-0 max-w-3xl">
            <HandGrid
              result={solverResult}
              selectedHand={selectedHand}
              actionOptions={viewedActionOptions}
              onSelectHand={setSelectedHand}
            />
          </div>
          <div className="w-[280px] shrink-0">
            <SolverResults
              result={solverResult}
              selectedHand={selectedHand}
              actionOptions={viewedActionOptions}
            />
          </div>
          {solverResult.debug && (
            <div className="w-[320px] shrink-0">
              <DebugPanels
                debug={solverResult.debug}
                actionOptions={viewedActionOptions}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
