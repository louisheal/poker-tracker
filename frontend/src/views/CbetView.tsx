import { getCbets } from "@/api";
import { SpeedDial } from "@/components/SpeedDial";
import { FilterGroup } from "@/components/FilterGroup";
import { useMemo } from "react";
import type {
  BoardTypeFilter,
  PotTypeFilter,
  CbetStats,
  PositionFilters,
  BoardTypeFilters,
  PotTypeFilters,
  DateRangeFilter,
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

interface CbetPanelProps {
  title: string;
  role: "PFR" | "DEF";
  stats: CbetStats | undefined;
}

const CbetPanel = ({ title, role, stats }: CbetPanelProps) => {
  const isPfr = role === "PFR";
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
      <div className="grid grid-cols-3 gap-4">
        <SpeedDial
          value={stats?.cbet_pct ?? 0}
          label={isPfr ? "Hero C-Bet" : "Villain C-Bet"}
        />
        <SpeedDial value={stats?.fcbet_pct ?? 0} label="Fold to C-Bet" />
        <SpeedDial
          value={stats?.raise_to_cbet_pct ?? 0}
          label={isPfr ? "Villain Raise" : "Hero Raise"}
        />
        <SpeedDial
          value={stats?.donk_bet_pct ?? 0}
          label={isPfr ? "Villain Donk Bet" : "Hero Donk Bet"}
        />
        <SpeedDial
          value={stats?.fold_to_donk_pct ?? 0}
          label="Fold to Donk Bet"
        />
        <SpeedDial
          value={stats?.raise_to_donk_pct ?? 0}
          label={isPfr ? "Hero Raise" : "Villain Raise"}
        />
      </div>
    </div>
  );
};

interface CbetViewProps {
  dateRange: DateRangeFilter;
}

export const CbetView = ({ dateRange }: CbetViewProps) => {
  const [pfrStats, setPfrStats] = useState<CbetStats>();
  const [defStats, setDefStats] = useState<CbetStats>();
  const [positionFilters, setPositionFilters] = useState<PositionFilters>(
    INITIAL_POSITION_FILTERS,
  );
  const [boardTypeFilters, setBoardTypeFilters] = useState<BoardTypeFilters>(
    INITIAL_BOARD_TYPE_FILTERS,
  );
  const [potTypeFilters, setPotTypeFilters] = useState<PotTypeFilters>(
    INITIAL_POT_TYPE_FILTERS,
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

  const { heroInPosition, boardTypes, potTypes } = useMemo(() => {
    const heroInPosition: boolean[] = [];
    const boardTypes: BoardTypeFilter[] = [];
    const potTypes: PotTypeFilter[] = [];

    if (positionFilters.ip) heroInPosition.push(true);
    if (positionFilters.oop) heroInPosition.push(false);

    if (boardTypeFilters.monotone) boardTypes.push("MONOTONE");
    if (boardTypeFilters.twoTone) boardTypes.push("TWO_TONE");
    if (boardTypeFilters.rainbow) boardTypes.push("RAINBOW");

    if (potTypeFilters.srp) potTypes.push("SRP");
    if (potTypeFilters.threeBet) potTypes.push("THREE_BET");
    if (potTypeFilters.fourBet) potTypes.push("FOUR_BET");

    return { heroInPosition, boardTypes, potTypes };
  }, [positionFilters, boardTypeFilters, potTypeFilters]);

  useEffect(() => {
    Promise.all([
      getCbets(
        heroInPosition,
        [true],
        boardTypes,
        potTypes,
        dateRange.startDate,
        dateRange.endDate,
      ),
      getCbets(
        heroInPosition,
        [false],
        boardTypes,
        potTypes,
        dateRange.startDate,
        dateRange.endDate,
      ),
    ]).then(([pfr, def]) => {
      setPfrStats(pfr);
      setDefStats(def);
    });
  }, [
    heroInPosition,
    boardTypes,
    potTypes,
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
      </div>

      <div className="grid gap-4 md:grid-cols-2 max-w-5xl">
        <CbetPanel role="PFR" title="PFR" stats={pfrStats} />
        <CbetPanel role="DEF" title="DEF" stats={defStats} />
      </div>
    </div>
  );
};
