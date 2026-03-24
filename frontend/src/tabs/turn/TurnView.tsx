import { getTurnStats } from "@/api";
import {
  positionOptions,
  boardTypeOptions,
  potTypeOptions,
  turnRunoutOptions,
} from "@/common/filterOptions";
import { FilterGroup } from "@/components/FilterGroup";
import type { TurnStats, DateRangeFilter, FlopActionLine } from "@/models";
import { useEffect, useState } from "react";
import { useToggleFilter } from "@/hooks/useToggleFilter";
import { TurnStatsPanel } from "./components/TurnStatsPanel";

const POSITION_MAP = { ip: true as const, oop: false as const };
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

const FLOP_ACTION_LINES: FlopActionLine[] = ["XX", "XBC", "XBRC", "BC"];

interface Props {
  dateRange: DateRangeFilter;
  includePool: boolean;
}

const INITIAL_POSITION_FILTERS = { ip: false, oop: false };
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

export const TurnView = ({ dateRange, includePool }: Props) => {
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
  const [turnRunoutFilters, toggleTurnRunout, turnRunouts] = useToggleFilter(
    INITIAL_TURN_RUNOUT_FILTERS,
    TURN_RUNOUT_MAP,
  );

  const [turnStats, setTurnStats] = useState<{
    [key in FlopActionLine]: TurnStats | undefined;
  }>({
    XX: undefined,
    XBC: undefined,
    XBRC: undefined,
    BC: undefined,
  });

  useEffect(() => {
    const fetchStats = async () => {
      const stats = await getTurnStats(
        heroInPosition,
        [true, false],
        boardTypes,
        potTypes,
        turnRunouts,
        dateRange.startDate,
        dateRange.endDate,
        includePool,
      );
      setTurnStats(stats);
    };

    fetchStats();
  }, [
    heroInPosition,
    boardTypes,
    potTypes,
    turnRunouts,
    dateRange.startDate,
    dateRange.endDate,
    includePool,
  ]);

  return (
    <div className="p-8 h-full content-start flex flex-col gap-6">
      <div className="flex flex-wrap gap-4">
        <FilterGroup
          options={positionOptions(positionFilters)}
          onToggle={togglePosition}
        />
        <FilterGroup
          options={boardTypeOptions(boardTypeFilters)}
          onToggle={toggleBoard}
        />
        <FilterGroup
          options={potTypeOptions(potTypeFilters)}
          onToggle={togglePot}
        />
        <FilterGroup
          options={turnRunoutOptions(turnRunoutFilters)}
          onToggle={toggleTurnRunout}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 max-w-5xl">
        {FLOP_ACTION_LINES.map((line) => (
          <TurnStatsPanel key={line} title={line} stats={turnStats[line]} />
        ))}
      </div>
    </div>
  );
};
