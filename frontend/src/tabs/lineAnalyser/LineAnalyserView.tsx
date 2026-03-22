import { useState, useMemo, useEffect } from "react";
import { FilterGroup } from "@/components/FilterGroup";
import { BetSizeDistribution } from "@/components/BetSizeDistribution";
import { getLineAnalysis, type LineAnalysisResponse } from "@/api";
import type {
  DateRangeFilter,
  ActionLine as ActionLineType,
  LineActionItem,
  TurnRunoutFilter,
  RiverRunoutFilter,
} from "@/models";
import { useToggleFilter } from "@/hooks/useToggleFilter";
import {
  potTypeOptions,
  boardTypeOptions,
  positionOptions,
  roleOptions,
  turnRunoutOptions,
  riverRunoutOptions,
} from "@/common/filterOptions";
import { ActionLine } from "./components/ActionLine";
import { StreetStatsPanel } from "./components/StreetStatsPanel";
import { EvPanel } from "./components/EvPanel";

const ACTION_LABELS: Record<string, string> = {
  X: "Check",
  B: "Bet",
  C: "Call",
  R: "Raise",
  F: "Fold",
};

const UNCAPPED_BET_SIZE = 999;
const TURN_MARKER = "TURN";
const RIVER_MARKER = "RIVER";

function buildActionLabel(
  actor: "hero" | "villain" | "",
  action: string,
  sizeRange?: [number, number],
): string {
  const actorStr = actor === "hero" ? "Hero" : "Villain";
  const actionStr = ACTION_LABELS[action] || action;
  if (sizeRange) {
    if (sizeRange[1] >= UNCAPPED_BET_SIZE) {
      return `${actorStr} ${actionStr} ${sizeRange[0]}%+`;
    }
    return `${actorStr} ${actionStr} ${sizeRange[0]}-${sizeRange[1]}%`;
  }
  return `${actorStr} ${actionStr}`;
}

function actionToPrefix(lineAction: LineActionItem): string {
  if (lineAction.actor === "marker") return lineAction.action;
  if (lineAction.sizeRange) {
    if (lineAction.sizeRange[1] >= UNCAPPED_BET_SIZE) {
      return `${lineAction.action}${lineAction.sizeRange[0]}+`;
    }
    return `${lineAction.action}${lineAction.sizeRange[0]}-${lineAction.sizeRange[1]}`;
  }
  return lineAction.action;
}

const BOARD_TYPE_MAP = {
  monotone: "MONOTONE" as const,
  twoTone: "TWO_TONE" as const,
  rainbow: "RAINBOW" as const,
};

const POT_TYPE_MAP = {
  SRP: "SRP" as const,
  THREE_BET: "THREE_BET" as const,
  FOUR_BET: "FOUR_BET" as const,
};

const TURN_RUNOUT_MAP = {
  OVERCARD: "OVERCARD" as const,
  FLUSH_COMPLETING: "FLUSH_COMPLETING" as const,
  PAIRED: "PAIRED" as const,
  OTHER: "OTHER" as const,
};

const RIVER_RUNOUT_MAP = {
  OVERCARD: "OVERCARD" as const,
  FLUSH_COMPLETING: "FLUSH_COMPLETING" as const,
  PAIRED: "PAIRED" as const,
  OTHER: "OTHER" as const,
};

const INITIAL_BOARD_TYPE_FILTERS = {
  monotone: false,
  twoTone: false,
  rainbow: false,
};

const INITIAL_POT_TYPE_FILTERS = {
  SRP: false,
  THREE_BET: false,
  FOUR_BET: false,
};

const INITIAL_TURN_RUNOUT_FILTERS = {
  OVERCARD: false,
  FLUSH_COMPLETING: false,
  PAIRED: false,
  OTHER: false,
};

const INITIAL_RIVER_RUNOUT_FILTERS = {
  OVERCARD: false,
  FLUSH_COMPLETING: false,
  PAIRED: false,
  OTHER: false,
};

const EMPTY_RESPONSE: LineAnalysisResponse = {
  hand_count: 0,
  street: "flop",
  street_stats: {},
  ev_stats: {
    overall_ev: 0,
    next_actions: [],
  },
  bet_sizes: [],
  next_actor: "villain" as const,
  action_depth: 0,
  flop_complete: false,
  turn_available: false,
  turn_complete: false,
  river_available: false,
};

interface Props {
  dateRange: DateRangeFilter;
}

export const LineAnalyserView = ({ dateRange }: Props) => {
  const [position, setPosition] = useState<string>("ip");
  const [role, setRole] = useState<string>("pfr");
  const [boardTypeFilters, toggleBoard, activeBoards] = useToggleFilter(
    INITIAL_BOARD_TYPE_FILTERS,
    BOARD_TYPE_MAP,
  );
  const [potTypeFilters, togglePot, activePots] = useToggleFilter(
    INITIAL_POT_TYPE_FILTERS,
    POT_TYPE_MAP,
  );
  const [turnRunoutFilters, toggleTurnRunout, activeTurnRunouts] =
    useToggleFilter(INITIAL_TURN_RUNOUT_FILTERS, TURN_RUNOUT_MAP);
  const [riverRunoutFilters, toggleRiverRunout, activeRiverRunouts] =
    useToggleFilter(INITIAL_RIVER_RUNOUT_FILTERS, RIVER_RUNOUT_MAP);
  const [data, setData] = useState<LineAnalysisResponse>(EMPTY_RESPONSE);

  const [actionLine, setActionLine] = useState<ActionLineType>({
    actions: [],
    cursor: 0,
  });

  const isOnTurn = useMemo(
    () =>
      actionLine.actions
        .slice(0, actionLine.cursor)
        .some((a) => a.action === TURN_MARKER),
    [actionLine.actions, actionLine.cursor],
  );

  const isOnRiver = useMemo(
    () =>
      actionLine.actions
        .slice(0, actionLine.cursor)
        .some((a) => a.action === RIVER_MARKER),
    [actionLine.actions, actionLine.cursor],
  );

  const resetLine = () => {
    setActionLine({
      actions: [],
      cursor: 0,
    });
  };

  const actionPrefix = useMemo(() => {
    if (actionLine.cursor === 0 || actionLine.actions.length === 0)
      return undefined;
    if (actionLine.cursor > actionLine.actions.length) return undefined;
    return actionLine.actions.slice(0, actionLine.cursor).map(actionToPrefix);
  }, [actionLine]);

  useEffect(() => {
    const fetchLineData = async () => {
      const turnRunouts: TurnRunoutFilter[] | undefined = isOnTurn
        ? activeTurnRunouts
        : undefined;
      const riverRunouts: RiverRunoutFilter[] | undefined = isOnRiver
        ? activeRiverRunouts
        : undefined;
      const result = await getLineAnalysis(
        position === "ip",
        role === "pfr",
        activeBoards,
        activePots,
        actionPrefix,
        turnRunouts,
        riverRunouts,
        dateRange.startDate,
        dateRange.endDate,
      );
      setData(result);
    };

    fetchLineData();
  }, [
    position,
    role,
    activeBoards,
    activePots,
    actionPrefix,
    dateRange,
    isOnTurn,
    activeTurnRunouts,
    isOnRiver,
    activeRiverRunouts,
  ]);

  const handleActionClick = (action: string, sizeRange?: [number, number]) => {
    const actor = data.next_actor;
    if (!actor) return;
    const newAction: LineActionItem = {
      actor,
      action,
      sizeRange,
      label: buildActionLabel(actor, action, sizeRange),
    };

    setActionLine((prev) => {
      const trimmed = prev.actions.slice(0, prev.cursor);
      return {
        ...prev,
        actions: [...trimmed, newAction],
        cursor: prev.cursor + 1,
      };
    });
  };

  const handleContinueToTurn = () => {
    setActionLine((prev) => {
      const trimmed = prev.actions.slice(0, prev.cursor);
      const turnMarker: LineActionItem = {
        actor: "marker",
        action: TURN_MARKER,
        label: "Turn",
      };
      return {
        ...prev,
        actions: [...trimmed, turnMarker],
        cursor: prev.cursor + 1,
      };
    });
  };

  const handleContinueToRiver = () => {
    setActionLine((prev) => {
      const trimmed = prev.actions.slice(0, prev.cursor);
      const riverMarker: LineActionItem = {
        actor: "marker",
        action: RIVER_MARKER,
        label: "River",
      };
      return {
        ...prev,
        actions: [...trimmed, riverMarker],
        cursor: prev.cursor + 1,
      };
    });
  };

  const handleClickTag = (index: number) => {
    setActionLine((prev) => ({
      ...prev,
      cursor: index,
    }));
  };

  const handleRemoveLast = () => {
    setActionLine((prev) => ({
      ...prev,
      actions: prev.actions.slice(0, -1),
      cursor: Math.min(prev.cursor, prev.actions.length - 1),
    }));
  };

  const handleClickFlop = () => {
    setActionLine((prev) => ({
      ...prev,
      cursor: 0,
    }));
  };

  const handlePositionChange = (key: string) => {
    setPosition(key);
    resetLine();
  };

  const handleRoleChange = (key: string) => {
    setRole(key);
    resetLine();
  };

  const betSizeTitle = useMemo(() => {
    const heroIsOop = position === "oop";
    const nextActor = data.next_actor;
    const isHeroNextToAct = nextActor === "hero";
    const actorName = isHeroNextToAct ? "Hero" : "Villain";

    const depth = actionLine.cursor;
    let actionType = "";

    if (depth === 0) {
      actionType = isHeroNextToAct && heroIsOop ? "Donk Bet" : "C-Bet";
      if (isHeroNextToAct && !heroIsOop) actionType = "C-Bet";
      if (!isHeroNextToAct && heroIsOop) actionType = "C-Bet";
      if (!isHeroNextToAct && !heroIsOop) actionType = "Donk Bet";
    } else {
      const lastAction = actionLine.actions[depth - 1];
      if (lastAction?.action === "X") {
        actionType = isHeroNextToAct && heroIsOop ? "Donk Bet" : "C-Bet";
        if (isHeroNextToAct && !heroIsOop) actionType = "C-Bet";
        if (!isHeroNextToAct && heroIsOop) actionType = "C-Bet";
        if (!isHeroNextToAct && !heroIsOop) actionType = "Donk Bet";
      } else if (
        lastAction?.action === "B" ||
        lastAction?.action.startsWith("B")
      ) {
        actionType = "Raise";
      } else if (
        lastAction?.action === "R" ||
        lastAction?.action.startsWith("R")
      ) {
        actionType = "Raise";
      }
    }

    return `${actorName} ${actionType} Size Distribution`;
  }, [position, data.next_actor, actionLine]);

  const showTurnTransition =
    data.flop_complete &&
    data.turn_available &&
    data.ev_stats.next_actions.length === 0 &&
    !isOnTurn;

  const showRiverTransition =
    data.turn_complete &&
    data.river_available &&
    data.ev_stats.next_actions.length === 0 &&
    !isOnRiver;

  return (
    <div className="p-8 h-full content-start flex flex-col gap-6">
      {/* General filters */}
      <div className="flex flex-col gap-3">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          General
        </span>
        <div className="flex flex-wrap items-end gap-4">
          <FilterGroup
            options={positionOptions(position)}
            onToggle={handlePositionChange}
          />
          <FilterGroup
            options={roleOptions(role)}
            onToggle={handleRoleChange}
          />
          <FilterGroup
            options={potTypeOptions(potTypeFilters)}
            onToggle={togglePot}
          />
        </div>
      </div>

      {/* Flop filters */}
      <div className="flex flex-col gap-3">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Flop
        </span>
        <div className="flex flex-wrap items-end gap-4">
          <FilterGroup
            options={boardTypeOptions(boardTypeFilters)}
            onToggle={toggleBoard}
          />
        </div>
      </div>

      {/* Turn filters */}
      <div className="flex flex-col gap-3">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Turn
        </span>
        <div className="flex flex-wrap items-end gap-4">
          <FilterGroup
            options={turnRunoutOptions(turnRunoutFilters)}
            onToggle={toggleTurnRunout}
          />
        </div>
      </div>

      {/* River filters */}
      <div className="flex flex-col gap-3">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          River
        </span>
        <div className="flex flex-wrap items-end gap-4">
          <FilterGroup
            options={riverRunoutOptions(riverRunoutFilters)}
            onToggle={toggleRiverRunout}
          />
        </div>
      </div>

      {/* Action line tags */}
      <ActionLine
        actionLine={actionLine}
        onClickFlop={handleClickFlop}
        onClickTag={handleClickTag}
        onRemoveLast={handleRemoveLast}
      />

      {/* Divider */}
      <div className="border-t border-border" />

      {/* Row 1: Street Stats + EV Panel */}
      <div className="grid gap-4 md:grid-cols-2 max-w-5xl">
        <StreetStatsPanel
          street={data.street}
          stats={{ hand_count: data.hand_count, ...data.street_stats }}
          isPfr={role === "pfr"}
        />
        <EvPanel
          nextActor={data.next_actor}
          overallEv={data.ev_stats.overall_ev}
          handCount={data.hand_count}
          nextActions={data.ev_stats.next_actions}
          onActionClick={handleActionClick}
          showTurnTransition={showTurnTransition}
          onContinueToTurn={handleContinueToTurn}
          showRiverTransition={showRiverTransition}
          onContinueToRiver={handleContinueToRiver}
        />
      </div>

      {/* Row 2: Bet size distribution */}
      <div className="max-w-5xl">
        <BetSizeDistribution sizes={data.bet_sizes} title={betSizeTitle} />
      </div>
    </div>
  );
};
