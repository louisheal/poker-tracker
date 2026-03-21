import { getCbets, getVillainBetSizes } from "@/api";
import { FilterGroup } from "@/components/FilterGroup";
import { BetSizeDistribution } from "@/components/BetSizeDistribution";
import { Slider } from "@/components/ui/slider";
import type { CbetStats, DateRangeFilter } from "@/models";
import { useEffect, useState } from "react";
import { useToggleFilter } from "@/hooks/useToggleFilter";
import { FlopStatsPanel } from "./components/FlopStatsPanel";

const POSITION_MAP = { ip: true as const, oop: false as const };
const BOARD_TYPE_MAP = {
  monotone: "MONOTONE" as const,
  twoTone: "TWO_TONE" as const,
  rainbow: "RAINBOW" as const,
};
const POT_TYPE_MAP = {
  srp: "SRP" as const,
  threeBet: "THREE_BET" as const,
  fourBet: "FOUR_BET" as const,
};

const BET_SIZE_MIN = 0;
const BET_SIZE_MAX = 200;

const INITIAL_POSITION_FILTERS = { ip: false, oop: false };
const INITIAL_BOARD_TYPE_FILTERS = {
  monotone: false,
  twoTone: false,
  rainbow: false,
};
const INITIAL_POT_TYPE_FILTERS = {
  srp: false,
  threeBet: false,
  fourBet: false,
};

interface Props {
  dateRange: DateRangeFilter;
}

export const FlopView = ({ dateRange }: Props) => {
  const [positionFilters, togglePosition, heroInPosition] = useToggleFilter(
    INITIAL_POSITION_FILTERS,
    POSITION_MAP,
  );
  const [boardTypeFilters, toggleBoard, boardTypes] = useToggleFilter(
    INITIAL_BOARD_TYPE_FILTERS,
    BOARD_TYPE_MAP,
  );
  const [potTypeFilters, togglePot, potTypes] = useToggleFilter(
    INITIAL_POT_TYPE_FILTERS,
    POT_TYPE_MAP,
  );

  const [pfrStats, setPfrStats] = useState<CbetStats>();
  const [defStats, setDefStats] = useState<CbetStats>();
  const [villainBetSizes, setVillainBetSizes] = useState<number[]>([]);
  const [betSizeRange, setBetSizeRange] = useState<[number, number]>([
    BET_SIZE_MIN,
    BET_SIZE_MAX,
  ]);

  const onBetSizeChange = (values: number[]) =>
    setBetSizeRange([values[0], values[1]]);

  const isDefaultBetSize =
    betSizeRange[0] === BET_SIZE_MIN && betSizeRange[1] === BET_SIZE_MAX;

  useEffect(() => {
    const betMin = isDefaultBetSize ? undefined : betSizeRange[0];
    const betMax = isDefaultBetSize ? undefined : betSizeRange[1];

    const fetchPfr = async () => {
      const pfr = await getCbets(
        heroInPosition,
        [true],
        boardTypes,
        potTypes,
        dateRange.startDate,
        dateRange.endDate,
        betMin,
        betMax,
      );
      setPfrStats(pfr);
    };

    const fetchDef = async () => {
      const def = await getCbets(
        heroInPosition,
        [false],
        boardTypes,
        potTypes,
        dateRange.startDate,
        dateRange.endDate,
        betMin,
        betMax,
      );
      setDefStats(def);
    };

    fetchPfr();
    fetchDef();
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
    const fetchBetSizes = async () => {
      const betSizes = await getVillainBetSizes(
        heroInPosition,
        boardTypes,
        potTypes,
        dateRange.startDate,
        dateRange.endDate,
      );
      setVillainBetSizes(betSizes.villain_bet_sizes);
    };

    fetchBetSizes();
  }, [
    heroInPosition,
    boardTypes,
    potTypes,
    dateRange.startDate,
    dateRange.endDate,
  ]);

  return (
    <div className="p-8 h-full content-start flex flex-col gap-6">
      <div className="flex flex-wrap items-end gap-4">
        <FilterGroup
          options={[
            { key: "ip", label: "IP", active: positionFilters.ip },
            { key: "oop", label: "OOP", active: positionFilters.oop },
          ]}
          onToggle={togglePosition}
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
          onToggle={toggleBoard}
        />

        <FilterGroup
          options={[
            { key: "srp", label: "SRP", active: potTypeFilters.srp },
            { key: "threeBet", label: "3BET", active: potTypeFilters.threeBet },
            { key: "fourBet", label: "4BET", active: potTypeFilters.fourBet },
          ]}
          onToggle={togglePot}
        />

        <div className="flex flex-col gap-1.5 min-w-48 max-w-64">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            Bet Size {betSizeRange[0]}% - {betSizeRange[1]}%
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
