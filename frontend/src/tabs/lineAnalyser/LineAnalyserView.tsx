import { useState, useMemo, useEffect, useCallback } from "react";
import { FilterGroup } from "@/components/FilterGroup";
import { BetSizeDistribution } from "@/components/BetSizeDistribution";
import {
  getLineAnalysisFlop,
  type LineAnalysisFlopResponse,
} from "@/api";
import type {
  BoardTypeFilter,
  BoardTypeFilters,
  PotTypeFilter,
  PotTypeFilters,
  DateRangeFilter,
  ActionLine as ActionLineType,
  LineActionItem,
} from "@/models";
import { RadioFilter } from "./components/RadioFilter";
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

function buildActionLabel(actor: "hero" | "villain" | "", action: string, sizeRange?: [number, number]): string {
  const actorStr = actor === "hero" ? "Hero" : "Villain";
  const actionStr = ACTION_LABELS[action] || action;
  if (sizeRange) {
    if (sizeRange[1] >= 999) {
      return `${actorStr} ${actionStr} ${sizeRange[0]}%+`;
    }
    return `${actorStr} ${actionStr} ${sizeRange[0]}-${sizeRange[1]}%`;
  }
  return `${actorStr} ${actionStr}`;
}

function actionToPrefix(la: LineActionItem): string {
  if (la.sizeRange) {
    if (la.sizeRange[1] >= 999) {
      return `${la.action}${la.sizeRange[0]}+`;
    }
    return `${la.action}${la.sizeRange[0]}-${la.sizeRange[1]}`;
  }
  return la.action;
}

const INITIAL_BOARD_TYPE_FILTERS: BoardTypeFilters = {
  monotone: false,
  twoTone: false,
  rainbow: false,
};

const INITIAL_POT_TYPE_FILTERS: PotTypeFilters = {
  srp: false,
  threeBet: false,
  fourBet: false,
};

const BOARD_TYPE_MAP: Record<string, BoardTypeFilter> = {
  monotone: "MONOTONE",
  twoTone: "TWO_TONE",
  rainbow: "RAINBOW",
};

const POT_TYPE_MAP: Record<string, PotTypeFilter> = {
  srp: "SRP",
  threeBet: "THREE_BET",
  fourBet: "FOUR_BET",
};

const EMPTY_RESPONSE: LineAnalysisFlopResponse = {
  hand_count: 0,
  street_stats: {
    cbet_pct: 0,
    fold_to_cbet_pct: 0,
    raise_to_cbet_pct: 0,
    fold_to_cbet_raise_pct: 0,
    donk_bet_pct: 0,
    fold_to_donk_pct: 0,
    raise_to_donk_pct: 0,
    fold_to_donk_raise_pct: 0,
  },
  ev_stats: {
    overall_ev: 0,
    next_actions: [],
  },
  bet_sizes: [],
  next_actor: "villain" as const,
  action_depth: 0,
};

interface Props {
  dateRange: DateRangeFilter;
}

export const LineAnalyserView = ({
  dateRange,
}: Props) => {
  const [position, setPosition] = useState<string>("ip");
  const [role, setRole] = useState<string>("pfr");
  const [boardTypeFilters, setBoardTypeFilters] = useState<BoardTypeFilters>(
    INITIAL_BOARD_TYPE_FILTERS,
  );
  const [potTypeFilters, setPotTypeFilters] = useState<PotTypeFilters>(
    INITIAL_POT_TYPE_FILTERS,
  );
  const [data, setData] = useState<LineAnalysisFlopResponse>(EMPTY_RESPONSE);

  const [actionLine, setActionLine] = useState<ActionLineType>({
    actions: [],
    cursor: -1,
  });

  const resetLine = useCallback(() => {
    setActionLine({
      actions: [],
      cursor: -1,
    });
  }, []);

  const toggleBoardTypeFilter = (key: string) => {
    setBoardTypeFilters((prev) => ({
      ...prev,
      [key as keyof BoardTypeFilters]: !prev[key as keyof BoardTypeFilters],
    }));
  };

  const togglePotTypeFilter = (key: string) => {
    setPotTypeFilters((prev) => ({
      ...prev,
      [key as keyof PotTypeFilters]: !prev[key as keyof PotTypeFilters],
    }));
  };

  const activeBoards = useMemo(() => {
    const active = Object.entries(boardTypeFilters)
      .filter(([, v]) => v)
      .map(([k]) => BOARD_TYPE_MAP[k]);
    return active.length > 0 ? active : Object.values(BOARD_TYPE_MAP);
  }, [boardTypeFilters]);

  const activePots = useMemo(() => {
    const active = Object.entries(potTypeFilters)
      .filter(([, v]) => v)
      .map(([k]) => POT_TYPE_MAP[k]);
    return active.length > 0 ? active : Object.values(POT_TYPE_MAP);
  }, [potTypeFilters]);

  const actionPrefix = useMemo(() => {
    if (actionLine.cursor < 0 || actionLine.actions.length === 0) return undefined;
    if (actionLine.cursor >= actionLine.actions.length) return undefined;
    return actionLine.actions.slice(0, actionLine.cursor + 1).map(actionToPrefix);
  }, [actionLine]);

  useEffect(() => {
    (async () => {
      try {
        const result = await getLineAnalysisFlop(
          position === "ip",
          role === "pfr",
          activeBoards,
          activePots,
          actionPrefix,
          dateRange.startDate,
          dateRange.endDate,
        );
        setData(result);
      } catch (err) {
        console.error("Failed to fetch line analysis data:", err);
      }
    })();
  }, [position, role, activeBoards, activePots, actionPrefix, dateRange]);

  const handleActionClick = useCallback((action: string, sizeRange?: [number, number]) => {
    const actor = data.next_actor;
    if (!actor) return;
    const newAction: LineActionItem = {
      actor,
      action,
      sizeRange,
      label: buildActionLabel(actor, action, sizeRange),
    };

    setActionLine((prev) => {
      const trimmed = prev.actions.slice(0, prev.cursor + 1);
      return {
        ...prev,
        actions: [...trimmed, newAction],
        cursor: prev.cursor + 1,
      };
    });
  }, [data.next_actor]);

  const handleClickTag = useCallback((index: number) => {
    setActionLine((prev) => ({
      ...prev,
      cursor: index,
    }));
  }, []);

  const handleRemoveLast = useCallback(() => {
    setActionLine((prev) => ({
      ...prev,
      actions: prev.actions.slice(0, -1),
      cursor: Math.min(prev.cursor, prev.actions.length - 2),
    }));
  }, []);

  const handleClickFlop = useCallback(() => {
    setActionLine((prev) => ({
      ...prev,
      cursor: -1,
    }));
  }, []);

  const handlePositionChange = useCallback((key: string) => {
    setPosition(key);
    resetLine();
  }, [resetLine]);

  const handleRoleChange = useCallback((key: string) => {
    setRole(key);
    resetLine();
  }, [resetLine]);

  const betSizeTitle = useMemo(() => {
    const heroIsOop = position === "oop";
    const nextActor = data.next_actor;
    const isHeroNextToAct = nextActor === "hero";
    const actorName = isHeroNextToAct ? "Hero" : "Villain";
    
    const depth = actionLine.cursor;
    let actionType = "";
    
    if (depth === -1) {
      actionType = isHeroNextToAct && heroIsOop ? "Donk Bet" : "C-Bet";
      if (isHeroNextToAct && !heroIsOop) actionType = "C-Bet";
      if (!isHeroNextToAct && heroIsOop) actionType = "C-Bet";
      if (!isHeroNextToAct && !heroIsOop) actionType = "Donk Bet";
    } else {
      const lastAction = actionLine.actions[depth];
      if (lastAction?.action === "X") {
        actionType = isHeroNextToAct && heroIsOop ? "Donk Bet" : "C-Bet";
        if (isHeroNextToAct && !heroIsOop) actionType = "C-Bet";
        if (!isHeroNextToAct && heroIsOop) actionType = "C-Bet";
        if (!isHeroNextToAct && !heroIsOop) actionType = "Donk Bet";
      } else if (lastAction?.action === "B" || lastAction?.action.startsWith("B")) {
        actionType = "Raise";
      } else if (lastAction?.action === "R" || lastAction?.action.startsWith("R")) {
        actionType = "Raise";
      }
    }
    
    return `${actorName} ${actionType} Size Distribution`;
  }, [position, data.next_actor, actionLine]);

  return (
    <div className="p-8 h-full content-start flex flex-col gap-6">
      {/* General filters */}
      <div className="flex flex-col gap-3">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          General
        </span>
        <div className="flex flex-wrap items-end gap-4">
          <RadioFilter
            options={[
              { key: "ip", label: "IP" },
              { key: "oop", label: "OOP" },
            ]}
            selected={position}
            onSelect={handlePositionChange}
          />
          <RadioFilter
            options={[
              { key: "pfr", label: "PFR" },
              { key: "def", label: "DEF" },
            ]}
            selected={role}
            onSelect={handleRoleChange}
          />
          <FilterGroup
            options={[
              { key: "srp", label: "SRP", active: potTypeFilters.srp },
              {
                key: "threeBet",
                label: "3BET",
                active: potTypeFilters.threeBet,
              },
              {
                key: "fourBet",
                label: "4BET",
                active: potTypeFilters.fourBet,
              },
            ]}
            onToggle={togglePotTypeFilter}
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
            options={[
              {
                key: "monotone",
                label: "MONOTONE",
                active: boardTypeFilters.monotone,
              },
              {
                key: "twoTone",
                label: "2TONE",
                active: boardTypeFilters.twoTone,
              },
              {
                key: "rainbow",
                label: "RAINBOW",
                active: boardTypeFilters.rainbow,
              },
            ]}
            onToggle={toggleBoardTypeFilter}
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
          stats={{ hand_count: data.hand_count, ...data.street_stats }}
          isPfr={role === "pfr"}
        />
        <EvPanel
          nextActor={data.next_actor}
          overallEv={data.ev_stats.overall_ev}
          handCount={data.hand_count}
          nextActions={data.ev_stats.next_actions}
          onActionClick={handleActionClick}
        />
      </div>

      {/* Row 2: Bet size distribution */}
      <div className="max-w-5xl">
        <BetSizeDistribution sizes={data.bet_sizes} title={betSizeTitle} />
      </div>
    </div>
  );
};
