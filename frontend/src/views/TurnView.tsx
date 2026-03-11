import { getTurnStats } from "@/api";
import { SpeedDial } from "@/components/SpeedDial";
import { FilterGroup } from "@/components/FilterGroup";
import { useMemo } from "react";
import type {
  BoardTypeFilter,
  PotTypeFilter,
  TurnStats,
  PositionFilters,
  BoardTypeFilters,
  PotTypeFilters,
  DateRangeFilter,
  FlopActionLine,
  TurnRunoutFilters,
  TurnRunoutFilter,
} from "@/models";
import { useEffect, useState } from "react";

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

const INITIAL_TURN_RUNOUT_FILTERS: TurnRunoutFilters = {
  overcard: false,
  flushCompleting: false,
  paired: false,
  other: false,
};

interface TurnPanelProps {
  title: string;
  stats: TurnStats | undefined;
}

const TurnPanel = ({ title, stats }: TurnPanelProps) => {
  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          {title}
        </h3>
        <p className="text-xs text-muted-foreground">
          {stats?.hand_count ?? 0} hands
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <SpeedDial value={stats?.hero_bet_pct ?? 0} label="Hero Bets Turn" />
        <SpeedDial
          value={stats?.villain_fold_to_hero_bet_pct ?? 0}
          label="Villain Fold to Bet"
        />
        <SpeedDial
          value={stats?.villain_bet_pct ?? 0}
          label="Villain Bets Turn"
        />
        <SpeedDial
          value={stats?.hero_fold_to_villain_bet_pct ?? 0}
          label="Hero Fold to Bet"
        />
      </div>
    </div>
  );
};

interface TurnViewProps {
  dateRange: DateRangeFilter;
}

const FLOP_ACTION_LINES: FlopActionLine[] = ["XX", "XBC", "XBRC", "BC"];

export const TurnView = ({ dateRange }: TurnViewProps) => {
  const [turnStats, setTurnStats] = useState<
    { [key in FlopActionLine]: TurnStats | undefined }
  >({
    XX: undefined,
    XBC: undefined,
    XBRC: undefined,
    BC: undefined,
  });
  const [positionFilters, setPositionFilters] = useState<PositionFilters>(
    INITIAL_POSITION_FILTERS,
  );
  const [boardTypeFilters, setBoardTypeFilters] = useState<BoardTypeFilters>(
    INITIAL_BOARD_TYPE_FILTERS,
  );
  const [potTypeFilters, setPotTypeFilters] = useState<PotTypeFilters>(
    INITIAL_POT_TYPE_FILTERS,
  );
  const [turnRunoutFilters, setTurnRunoutFilters] = useState<TurnRunoutFilters>(
    INITIAL_TURN_RUNOUT_FILTERS,
  );

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

  const toggleTurnRunoutFilter = (key: string) => {
    setTurnRunoutFilters((prev) => ({
      ...prev,
      [key as keyof TurnRunoutFilters]: !prev[key as keyof TurnRunoutFilters],
    }));
  };

  const { heroInPosition, boardTypes, potTypes, turnRunouts } = useMemo(() => {
    const heroInPosition: boolean[] = [];
    const boardTypes: BoardTypeFilter[] = [];
    const potTypes: PotTypeFilter[] = [];
    const turnRunouts: TurnRunoutFilter[] = [];

    if (positionFilters.ip) heroInPosition.push(true);
    if (positionFilters.oop) heroInPosition.push(false);

    if (boardTypeFilters.monotone) boardTypes.push("MONOTONE");
    if (boardTypeFilters.twoTone) boardTypes.push("TWO_TONE");
    if (boardTypeFilters.rainbow) boardTypes.push("RAINBOW");

    if (potTypeFilters.srp) potTypes.push("SRP");
    if (potTypeFilters.threeBet) potTypes.push("THREE_BET");
    if (potTypeFilters.fourBet) potTypes.push("FOUR_BET");

    if (turnRunoutFilters.overcard) turnRunouts.push("OVERCARD");
    if (turnRunoutFilters.flushCompleting) turnRunouts.push("FLUSH_COMPLETING");
    if (turnRunoutFilters.paired) turnRunouts.push("PAIRED");
    if (turnRunoutFilters.other) turnRunouts.push("OTHER");

    return { heroInPosition, boardTypes, potTypes, turnRunouts };
  }, [positionFilters, boardTypeFilters, potTypeFilters, turnRunoutFilters]);

  useEffect(() => {
    getTurnStats(
      heroInPosition,
      [true, false],
      boardTypes,
      potTypes,
      turnRunouts,
      dateRange.startDate,
      dateRange.endDate,
    ).then((stats) => {
      setTurnStats(stats);
    });
  }, [
    heroInPosition,
    boardTypes,
    potTypes,
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
        {FLOP_ACTION_LINES.map((line) => (
          <TurnPanel key={line} title={line} stats={turnStats[line]} />
        ))}
      </div>
    </div>
  );
};
