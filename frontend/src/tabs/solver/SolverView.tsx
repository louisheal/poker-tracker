import { useState, useMemo, useEffect, useCallback } from "react";
import type { CardJson } from "@/api";
import { getSolverResult } from "@/api";
import type { SolverResult } from "@/models";
import type { SolverSpot, ActionTile, BoardTile } from "./types";
import { INITIAL_SPOT } from "./types";
import { buildTiles } from "./gameTree";
import { ActionSequence } from "./components/ActionSequence";
import { HandGrid } from "./components/HandGrid";
import { SolverResults } from "./components/SolverResults";

export const SolverView = () => {
  const [spot, setSpot] = useState<SolverSpot>(INITIAL_SPOT);
  const [viewTileId, setViewTileId] = useState<string | null>(null);
  const [selectedHand, setSelectedHand] = useState<string | null>(null);
  const [solverResult, setSolverResult] = useState<SolverResult | null>(null);
  const [loading, setLoading] = useState(false);

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

  // The action options for the viewed decision point
  const viewedActionOptions = useMemo(() => {
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
    const board = allBoardCards.map(
      (c) => `${c.Rank}${c.Suit.toLowerCase()}`,
    );
    return {
      board,
      street: viewedTile.section,
      actions,
    };
  }, [viewedTile, tiles, allBoardCards]);

  useEffect(() => {
    if (!solverParams) {
      setSolverResult(null);
      return;
    }

    const controller = new AbortController();
    setLoading(true);

    const fetchResult = async () => {
      try {
        const result = await getSolverResult(solverParams, controller.signal);
        setSolverResult(result);
        setSelectedHand(null);
      } catch {
        // Aborted or error
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
    return () => controller.abort();
  }, [solverParams]);

  const handleNavigate = useCallback((tileId: string) => {
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
        <div className="text-sm text-muted-foreground py-6 text-center">
          Solving...
        </div>
      )}

      {/* Results */}
      {solverResult && !loading && hasDecisionPoint && (
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
        </div>
      )}
    </div>
  );
};
