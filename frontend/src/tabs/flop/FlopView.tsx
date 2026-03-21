import { getCbets, getVillainBetSizes } from "@/api";
import { FilterGroup } from "@/components/FilterGroup";
import { BetSizeDistribution } from "@/components/BetSizeDistribution";
import { Slider } from "@/components/ui/slider";
import { useMemo, useCallback } from "react";
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
import { FlopStatsPanel } from "./components/FlopStatsPanel";

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

const BET_SIZE_MIN = 0;
const BET_SIZE_MAX = 200;

interface Props {
  dateRange: DateRangeFilter;
}

export const FlopView = ({ dateRange }: Props) => {
  const [pfrStats, setPfrStats] = useState<CbetStats>();
  const [defStats, setDefStats] = useState<CbetStats>();
  const [villainBetSizes, setVillainBetSizes] = useState<number[]>([]);
  const [positionFilters, setPositionFilters] = useState<PositionFilters>(
    INITIAL_POSITION_FILTERS,
  );
  const [boardTypeFilters, setBoardTypeFilters] = useState<BoardTypeFilters>(
    INITIAL_BOARD_TYPE_FILTERS,
  );
  const [potTypeFilters, setPotTypeFilters] = useState<PotTypeFilters>(
    INITIAL_POT_TYPE_FILTERS,
  );
  const [betSizeRange, setBetSizeRange] = useState<[number, number]>([
    BET_SIZE_MIN,
    BET_SIZE_MAX,
  ]);

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

  const onBetSizeChange = useCallback((values: number[]) => {
    setBetSizeRange([values[0], values[1]]);
  }, []);

  const isDefaultBetSize =
    betSizeRange[0] === BET_SIZE_MIN && betSizeRange[1] === BET_SIZE_MAX;

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
    const betMin = isDefaultBetSize ? undefined : betSizeRange[0];
    const betMax = isDefaultBetSize ? undefined : betSizeRange[1];

    Promise.all([
      getCbets(
        heroInPosition,
        [true],
        boardTypes,
        potTypes,
        dateRange.startDate,
        dateRange.endDate,
        betMin,
        betMax,
      ),
      getCbets(
        heroInPosition,
        [false],
        boardTypes,
        potTypes,
        dateRange.startDate,
        dateRange.endDate,
        betMin,
        betMax,
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
    betSizeRange,
    isDefaultBetSize,
  ]);

  useEffect(() => {
    getVillainBetSizes(
      heroInPosition,
      boardTypes,
      potTypes,
      dateRange.startDate,
      dateRange.endDate,
    ).then((res) => setVillainBetSizes(res.villain_bet_sizes));
  }, [heroInPosition, boardTypes, potTypes, dateRange.startDate, dateRange.endDate]);

  return (
    <div className="p-8 h-full content-start flex flex-col gap-6">
      <div className="flex flex-wrap items-end gap-4">
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

        <div className="flex flex-col gap-1.5 min-w-48 max-w-64">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            Bet Size {betSizeRange[0]}% – {betSizeRange[1]}%
          </span>
          <Slider
            min={BET_SIZE_MIN}
            max={BET_SIZE_MAX}
            step={5}
            value={betSizeRange}
            onValueChange={onBetSizeChange}
          />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 max-w-5xl">
        <FlopStatsPanel role="PFR" title="PFR" stats={pfrStats} />
        <FlopStatsPanel role="DEF" title="DEF" stats={defStats} />
      </div>

      <div className="max-w-5xl">
        <BetSizeDistribution sizes={villainBetSizes} />
      </div>
    </div>
  );
};
