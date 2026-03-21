import { useState, useMemo, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { FilterGroup } from "@/components/FilterGroup";
import { SpeedDial } from "@/components/SpeedDial";
import { BetSizeDistribution } from "@/components/BetSizeDistribution";
import {
  getLineAnalysisFlop,
  type LineAnalysisFlopResponse,
  type NextAction,
} from "@/api";
import type {
  BoardTypeFilter,
  BoardTypeFilters,
  PotTypeFilter,
  PotTypeFilters,
  DateRangeFilter,
  ActionLine,
  LineActionItem,
} from "@/models";

// --- Single-select filter (always one selected) ---

interface RadioFilterProps {
  options: { key: string; label: string }[];
  selected: string;
  onSelect: (key: string) => void;
}

const RadioFilter = ({ options, selected, onSelect }: RadioFilterProps) => (
  <div className="flex items-center gap-2">
    {options.map((opt) => (
      <Button
        key={opt.key}
        variant={selected === opt.key ? "outline" : "default"}
        onClick={() => onSelect(opt.key)}
      >
        {opt.label}
      </Button>
    ))}
  </div>
);

// --- Action line types ---

interface ActionTagProps {
  label: string;
  isActive: boolean;
  isFuture: boolean;
  onClick: () => void;
  onRemove?: () => void;
  showArrow?: boolean;
}

const ActionTag = ({ label, isActive, isFuture, onClick, onRemove, showArrow = true }: ActionTagProps) => (
  <div className="flex items-center gap-1">
    {showArrow && (
      <span className={`text-xs ${isFuture ? "text-muted-foreground/40" : "text-muted-foreground"}`}>→</span>
    )}
    <button
      onClick={onClick}
      className={`
        inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors
        ${isActive
          ? "bg-primary text-primary-foreground"
          : isFuture
            ? "bg-muted/40 text-muted-foreground/50 hover:bg-muted/60"
            : "bg-muted text-muted-foreground hover:bg-muted/80"
        }
      `}
    >
      {label}
      {onRemove && (
        <span
          role="button"
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="ml-1 hover:text-destructive cursor-pointer"
        >
          ×
        </span>
      )}
    </button>
  </div>
);

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

// --- Action line tag bar ---

interface ActionLineProps {
  actionLine: ActionLine;
  onClickFlop: () => void;
  onClickTag: (index: number) => void;
  onRemoveLast: () => void;
}

const ActionLineComponent = ({ actionLine, onClickFlop, onClickTag, onRemoveLast }: ActionLineProps) => {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {/* Flop - cursor = -1 means at flop */}
      <ActionTag
        label="Flop"
        isActive={actionLine.cursor === -1}
        isFuture={false}
        onClick={onClickFlop}
        showArrow={false}
      />

      {/* Action tags */}
      {actionLine.actions.map((la, i) => {
        const isActive = i === actionLine.cursor;
        const isFuture = i > actionLine.cursor;
        return (
          <ActionTag
            key={i}
            label={la.label}
            isActive={isActive}
            isFuture={isFuture}
            onClick={() => onClickTag(i)}
            onRemove={i === actionLine.actions.length - 1 ? onRemoveLast : undefined}
            showArrow={true}
          />
        );
      })}
    </div>
  );
};

// --- EV Row ---

interface EvRowProps {
  label: string;
  evBb: number;
  count: number;
  onClick?: () => void;
}

const EvRow = ({ label, evBb, count, onClick }: EvRowProps) => {
  const color =
    evBb > 0
      ? "text-emerald-400"
      : evBb < 0
        ? "text-red-400"
        : "text-muted-foreground";
  return (
    <div
      className={`flex items-center justify-between py-2 ${onClick ? "cursor-pointer hover:bg-muted/50 rounded px-2 -mx-2 transition-colors" : ""}`}
      onClick={onClick}
    >
      <div className="flex items-baseline gap-2">
        <span className="text-sm">{label}</span>
        <span className="text-xs text-muted-foreground">{count} hands</span>
      </div>
      <span className={`text-sm font-semibold tabular-nums ${color}`}>
        {evBb > 0 ? "+" : ""}
        {evBb.toFixed(1)} BB
      </span>
    </div>
  );
};

// --- Street stats panel ---

interface StreetStats {
  hand_count: number;
  cbet_pct: number;
  fold_to_cbet_pct: number;
  raise_to_cbet_pct: number;
  fold_to_cbet_raise_pct: number;
  donk_bet_pct: number;
  fold_to_donk_pct: number;
  raise_to_donk_pct: number;
  fold_to_donk_raise_pct: number;
}

interface StreetStatsPanelProps {
  stats: StreetStats;
  isPfr: boolean;
}

const StreetStatsPanel = ({ stats, isPfr }: StreetStatsPanelProps) => (
  <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-6">
    <div className="flex flex-col gap-1">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
        {isPfr ? "PFR" : "DEF"} — Flop Stats
      </h3>
      <p className="text-xs text-muted-foreground">
        {stats.hand_count} hands
      </p>
    </div>
    {/* C-bet row */}
    <div className="grid grid-cols-4 gap-4">
      <SpeedDial
        value={stats.cbet_pct}
        label={isPfr ? "Hero C-Bet" : "Villain C-Bet"}
      />
      <SpeedDial value={stats.fold_to_cbet_pct} label="Fold to C-Bet" />
      <SpeedDial
        value={stats.raise_to_cbet_pct}
        label={isPfr ? "Villain Raise" : "Hero Raise"}
      />
      <SpeedDial
        value={stats.fold_to_cbet_raise_pct}
        label={isPfr ? "Hero F2R" : "Villain F2R"}
      />
    </div>
    {/* Donk row */}
    <div className="grid grid-cols-4 gap-4">
      <SpeedDial
        value={stats.donk_bet_pct}
        label={isPfr ? "Villain Donk" : "Hero Donk"}
      />
      <SpeedDial value={stats.fold_to_donk_pct} label="Fold to Donk" />
      <SpeedDial
        value={stats.raise_to_donk_pct}
        label={isPfr ? "Hero Raise" : "Villain Raise"}
      />
      <SpeedDial
        value={stats.fold_to_donk_raise_pct}
        label={isPfr ? "Villain F2R" : "Hero F2R"}
      />
    </div>
  </div>
);

// --- Dynamic EV panel ---

const BET_ACTION_LABELS: Record<string, string> = {
  "B0-50": "Bet Small (0-50%)",
  "B50-100": "Bet Medium (50-100%)",
  "B100-200": "Bet Large (100-200%)",
  "B200+": "Bet Overbet (200%+)",
  "R0-50": "Raise Small (0-50%)",
  "R50-100": "Raise Medium (50-100%)",
  "R100-200": "Raise Large (100-200%)",
  "R200+": "Raise Overbet (200%+)",
};

function getActionLabel(action: string): string {
  return BET_ACTION_LABELS[action] || ACTION_LABELS[action] || action;
}

function parseActionKey(action: string): { base: string; sizeRange?: [number, number] } {
  // "B50-100" → { base: "B", sizeRange: [50, 100] }
  // "B200+" → { base: "B", sizeRange: [200, 999] }
  // "X" → { base: "X" }
  const match = action.match(/^([BRCXF])(\d+-\d+|\d+\+)?$/);
  if (!match) return { base: action };
  const base = match[1];
  const sizePart = match[2];
  if (!sizePart) return { base };
  if (sizePart.endsWith("+")) {
    const lo = parseInt(sizePart.slice(0, -1));
    return { base, sizeRange: [lo, 999] };
  }
  const [lo, hi] = sizePart.split("-").map(Number);
  return { base, sizeRange: [lo, hi] };
}

interface EvPanelProps {
  nextActor: "hero" | "villain" | "";
  overallEv: number;
  handCount: number;
  nextActions: NextAction[];
  onActionClick: (action: string, sizeRange?: [number, number]) => void;
}

const EvPanel = ({
  nextActor,
  overallEv,
  handCount,
  nextActions,
  onActionClick,
}: EvPanelProps) => {
  const actorLabel = nextActor === "hero" ? "Hero" : "Villain";
  const overallColor =
    overallEv > 0
      ? "text-emerald-400"
      : overallEv < 0
        ? "text-red-400"
        : "text-muted-foreground";

  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-4">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Expected Value
        </h3>
        <span className="text-xs text-muted-foreground">
          {handCount} hands
        </span>
      </div>

      {/* Overall EV */}
      <div className="bg-background/50 border border-border rounded-lg px-4 py-3 flex items-center justify-between">
        <span className="text-sm font-semibold">Overall</span>
        <span className={`text-lg font-bold tabular-nums ${overallColor}`}>
          {overallEv > 0 ? "+" : ""}
          {overallEv.toFixed(1)} BB
        </span>
      </div>

      {/* Dynamic per-action EV */}
      <div className="flex flex-col divide-y divide-border">
        {nextActions.map((na) => {
          const { base, sizeRange } = parseActionKey(na.action);
          return (
            <EvRow
              key={na.action}
              label={`${actorLabel} ${getActionLabel(na.action)}`}
              evBb={na.ev}
              count={na.count}
              onClick={() => onActionClick(base, sizeRange)}
            />
          );
        })}
        {nextActions.length === 0 && (
          <p className="text-xs text-muted-foreground py-2">
            No further actions (hand complete)
          </p>
        )}
      </div>
    </div>
  );
};

// --- Filter defaults ---

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

// --- Main view ---

interface LineAnalyserViewProps {
  dateRange: DateRangeFilter;
}

export const LineAnalyserView = ({
  dateRange,
}: LineAnalyserViewProps) => {
  const [position, setPosition] = useState<string>("ip");
  const [role, setRole] = useState<string>("pfr");
  const [boardTypeFilters, setBoardTypeFilters] = useState<BoardTypeFilters>(
    INITIAL_BOARD_TYPE_FILTERS,
  );
  const [potTypeFilters, setPotTypeFilters] = useState<PotTypeFilters>(
    INITIAL_POT_TYPE_FILTERS,
  );
  const [data, setData] = useState<LineAnalysisFlopResponse>(EMPTY_RESPONSE);

  // Action line state - cursor starts at -1 (Flop selected)
  const [actionLine, setActionLine] = useState<ActionLine>({
    actions: [],
    cursor: -1,
  });

  // Reset line when position/role change
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

  // Build filter arrays for API
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

  // Build action prefix from actions up to cursor
  const actionPrefix = useMemo(() => {
    if (actionLine.cursor < 0 || actionLine.actions.length === 0) return undefined;
    // cursor is now 0-indexed into actions, so cursor + 1 is the count
    if (actionLine.cursor >= actionLine.actions.length) return undefined;
    return actionLine.actions.slice(0, actionLine.cursor + 1).map(actionToPrefix);
  }, [actionLine]);

  const fetchData = useCallback(async () => {
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
  }, [position, role, activeBoards, activePots, actionPrefix, dateRange]);

  useEffect(() => {
    fetchData();
  }, [position, role, activeBoards, activePots, actionPrefix, dateRange]);

  // Handle clicking an action in the EV panel
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

  // Navigate to a tag
  const handleClickTag = useCallback((index: number) => {
    setActionLine((prev) => ({
      ...prev,
      cursor: index,
    }));
  }, []);

  // Remove last tag
  const handleRemoveLast = useCallback(() => {
    setActionLine((prev) => ({
      ...prev,
      actions: prev.actions.slice(0, -1),
      cursor: Math.min(prev.cursor, prev.actions.length - 2),
    }));
  }, []);

  // Reset to flop (cursor = -1, before any actions)
  const handleClickFlop = useCallback(() => {
    setActionLine((prev) => ({
      ...prev,
      cursor: -1,
    }));
  }, []);

  // Reset line on position/role change (action line depends on who acts first)
  const handlePositionChange = useCallback((key: string) => {
    setPosition(key);
    resetLine();
  }, [resetLine]);

  const handleRoleChange = useCallback((key: string) => {
    setRole(key);
    resetLine();
  }, [resetLine]);

  // Determine bet size chart title based on context
  const betSizeTitle = useMemo(() => {
    const isHeroPfr = role === "pfr";
    const heroIsOop = position === "oop";
    if (heroIsOop) {
      return isHeroPfr ? "Hero C-Bet Size Distribution" : "Hero Donk Bet Size Distribution";
    } else {
      return isHeroPfr ? "Villain Donk Bet Size Distribution" : "Villain C-Bet Size Distribution";
    }
  }, [position, role]);

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
      <ActionLineComponent
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
