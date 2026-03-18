import { getRiverStats } from "@/api";
import { SpeedDial } from "@/components/SpeedDial";
import { FilterGroup } from "@/components/FilterGroup";
import { useMemo } from "react";
import type {
  BoardTypeFilter,
  PotTypeFilter,
  RiverActionStats,
  PositionFilters,
  BoardTypeFilters,
  PotTypeFilters,
  DateRangeFilter,
  FlopActionFilters,
  FlopActionLine,
  TurnRunoutFilters,
  TurnRunoutFilter,
  ShowdownStats,
  ShowdownType,
} from "@/models";
import { useEffect, useState } from "react";
import type { RiverStats } from "@/models";

const INITIAL_POSITION_FILTERS: PositionFilters = { ip: false, oop: false };

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

const INITIAL_FLOP_ACTION_FILTERS: FlopActionFilters = {
  xx: false,
  xbc: false,
  xbrc: false,
  bc: false,
};

const INITIAL_TURN_RUNOUT_FILTERS: TurnRunoutFilters = {
  overcard: false,
  flushCompleting: false,
  paired: false,
  other: false,
};

interface RiverActionPanelProps {
  stats: RiverActionStats | undefined;
}

const RiverActionPanel = ({ stats }: RiverActionPanelProps) => {
  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          River Actions
        </h3>
        <p className="text-xs text-muted-foreground">
          {stats?.hand_count ?? 0} hands
        </p>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <SpeedDial value={stats?.hero_bet_pct ?? 0} label="Hero Bet" />
        <SpeedDial
          value={stats?.villain_fold_to_hero_bet_pct ?? 0}
          label="Villain Fold"
        />
        <SpeedDial
          value={stats?.villain_raise_to_hero_bet_pct ?? 0}
          label="Villain Raise"
        />
      </div>
      <div className="border-t border-border" />
      <div className="grid grid-cols-3 gap-4">
        <SpeedDial value={stats?.villain_bet_pct ?? 0} label="Villain Bet" />
        <SpeedDial
          value={stats?.hero_fold_to_villain_bet_pct ?? 0}
          label="Hero Fold"
        />
        <SpeedDial
          value={stats?.hero_raise_to_villain_bet_pct ?? 0}
          label="Hero Raise"
        />
      </div>
    </div>
  );
};

const SHOWDOWN_TYPES: { key: ShowdownType; label: string }[] = [
  { key: "CHECK_CHECK", label: "Check-Check" },
  { key: "BET_CALL", label: "Bet-Call" },
  { key: "RAISE_OCCURRED", label: "Raise Occurred" },
];

interface ShowdownPanelProps {
  showdown: { [key in ShowdownType]: ShowdownStats } | undefined;
}

const ShowdownPanel = ({ showdown }: ShowdownPanelProps) => {
  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Showdown Results (BB/hand)
        </h3>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {SHOWDOWN_TYPES.map(({ key, label }) => {
          const stats = showdown?.[key];
          const value = stats?.bb_per_hand ?? 0;
          const isPositive = value > 0;
          const isNegative = value < 0;
          return (
            <div key={key} className="flex flex-col items-center gap-2">
              <div className="w-25 h-25 rounded-full border-[7px] border-border flex items-center justify-center">
                <span
                  className={`text-lg font-bold ${isPositive ? "text-green-500" : isNegative ? "text-red-500" : "text-foreground"}`}
                >
                  {value >= 0 ? "+" : ""}
                  {value.toFixed(1)}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">{label}</span>
              <span className="text-xs text-muted-foreground">
                {stats?.hand_count ?? 0} hands
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

interface RiverViewProps {
  dateRange: DateRangeFilter;
}

export const RiverView = ({ dateRange }: RiverViewProps) => {
  const [riverStats, setRiverStats] = useState<RiverStats>();
  const [positionFilters, setPositionFilters] = useState<PositionFilters>(
    INITIAL_POSITION_FILTERS,
  );
  const [boardTypeFilters, setBoardTypeFilters] = useState<BoardTypeFilters>(
    INITIAL_BOARD_TYPE_FILTERS,
  );
  const [potTypeFilters, setPotTypeFilters] = useState<PotTypeFilters>(
    INITIAL_POT_TYPE_FILTERS,
  );
  const [flopActionFilters, setFlopActionFilters] =
    useState<FlopActionFilters>(INITIAL_FLOP_ACTION_FILTERS);
  const [turnRunoutFilters, setTurnRunoutFilters] =
    useState<TurnRunoutFilters>(INITIAL_TURN_RUNOUT_FILTERS);

  const togglePositionFilter = (key: string) => {
    setPositionFilters((prev) => ({
      ...prev,
      [key as keyof PositionFilters]: !prev[key as keyof PositionFilters],
    }));
  };

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

  const toggleFlopActionFilter = (key: string) => {
    setFlopActionFilters((prev) => ({
      ...prev,
      [key as keyof FlopActionFilters]: !prev[key as keyof FlopActionFilters],
    }));
  };

  const toggleTurnRunoutFilter = (key: string) => {
    setTurnRunoutFilters((prev) => ({
      ...prev,
      [key as keyof TurnRunoutFilters]: !prev[key as keyof TurnRunoutFilters],
    }));
  };

  const { heroInPosition, boardTypes, potTypes, flopActions, turnRunouts } =
    useMemo(() => {
      const heroInPosition: boolean[] = [];
      const boardTypes: BoardTypeFilter[] = [];
      const potTypes: PotTypeFilter[] = [];
      const flopActions: FlopActionLine[] = [];
      const turnRunouts: TurnRunoutFilter[] = [];

      if (positionFilters.ip) heroInPosition.push(true);
      if (positionFilters.oop) heroInPosition.push(false);

      if (boardTypeFilters.monotone) boardTypes.push("MONOTONE");
      if (boardTypeFilters.twoTone) boardTypes.push("TWO_TONE");
      if (boardTypeFilters.rainbow) boardTypes.push("RAINBOW");

      if (potTypeFilters.srp) potTypes.push("SRP");
      if (potTypeFilters.threeBet) potTypes.push("THREE_BET");
      if (potTypeFilters.fourBet) potTypes.push("FOUR_BET");

      if (flopActionFilters.xx) flopActions.push("XX");
      if (flopActionFilters.xbc) flopActions.push("XBC");
      if (flopActionFilters.xbrc) flopActions.push("XBRC");
      if (flopActionFilters.bc) flopActions.push("BC");

      if (turnRunoutFilters.overcard) turnRunouts.push("OVERCARD");
      if (turnRunoutFilters.flushCompleting)
        turnRunouts.push("FLUSH_COMPLETING");
      if (turnRunoutFilters.paired) turnRunouts.push("PAIRED");
      if (turnRunoutFilters.other) turnRunouts.push("OTHER");

      return { heroInPosition, boardTypes, potTypes, flopActions, turnRunouts };
    }, [
      positionFilters,
      boardTypeFilters,
      potTypeFilters,
      flopActionFilters,
      turnRunoutFilters,
    ]);

  useEffect(() => {
    getRiverStats(
      heroInPosition,
      boardTypes,
      potTypes,
      flopActions,
      turnRunouts,
      dateRange.startDate,
      dateRange.endDate,
    ).then((stats) => {
      setRiverStats(stats);
    });
  }, [
    heroInPosition,
    boardTypes,
    potTypes,
    flopActions,
    turnRunouts,
    dateRange.startDate,
    dateRange.endDate,
  ]);

  return (
    <div className="p-8 h-full content-start flex flex-col gap-6">
      <div className="flex flex-wrap gap-4">
        <FilterGroup
          options={[
            { key: "ip", label: "IP", active: positionFilters.ip },
            { key: "oop", label: "OOP", active: positionFilters.oop },
          ]}
          onToggle={togglePositionFilter}
        />

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

        <FilterGroup
          options={[
            { key: "srp", label: "SRP", active: potTypeFilters.srp },
            { key: "threeBet", label: "3BET", active: potTypeFilters.threeBet },
            { key: "fourBet", label: "4BET", active: potTypeFilters.fourBet },
          ]}
          onToggle={togglePotTypeFilter}
        />

        <FilterGroup
          options={[
            { key: "xx", label: "XX", active: flopActionFilters.xx },
            { key: "xbc", label: "XBC", active: flopActionFilters.xbc },
            { key: "xbrc", label: "XBRC", active: flopActionFilters.xbrc },
            { key: "bc", label: "BC", active: flopActionFilters.bc },
          ]}
          onToggle={toggleFlopActionFilter}
        />

        <FilterGroup
          options={[
            {
              key: "overcard",
              label: "OVERCARD",
              active: turnRunoutFilters.overcard,
            },
            {
              key: "flushCompleting",
              label: "FLUSH",
              active: turnRunoutFilters.flushCompleting,
            },
            {
              key: "paired",
              label: "PAIRED",
              active: turnRunoutFilters.paired,
            },
            {
              key: "other",
              label: "OTHER",
              active: turnRunoutFilters.other,
            },
          ]}
          onToggle={toggleTurnRunoutFilter}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 max-w-5xl">
        <RiverActionPanel stats={riverStats?.actions} />
        <ShowdownPanel showdown={riverStats?.showdown} />
      </div>
    </div>
  );
};
