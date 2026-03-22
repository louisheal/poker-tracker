import { getRiverStats } from "@/api";
import {
  positionOptions,
  boardTypeOptions,
  actionLineOptions,
  flopRankTextureOptions,
  turnRunoutOptions,
} from "@/common/filterOptions";
import { FilterGroup } from "@/components/FilterGroup";
import { useToggleFilter } from "@/hooks/useToggleFilter";
import type { DateRangeFilter, RiverStats } from "@/models";
import { useEffect, useState } from "react";
import { RiverActionPanel } from "./components/RiverActionPanel";
import { ShowdownPanel } from "./components/ShowdownPanel";
import { AvgPotPanel } from "./components/AvgPotPanel";

const POSITION_MAP = { ip: true as const, oop: false as const };
const BOARD_TYPE_MAP = {
  monotone: "MONOTONE" as const,
  twoTone: "TWO_TONE" as const,
  rainbow: "RAINBOW" as const,
};
const FLOP_ACTION_MAP = {
  xx: "XX" as const,
  xbc: "XBC" as const,
  xbrc: "XBRC" as const,
  bc: "BC" as const,
};
const FLOP_RANK_TEXTURE_MAP = {
  trips: "TRIPS" as const,
  paired: "PAIRED" as const,
  unpaired: "UNPAIRED" as const,
};
const TURN_ACTION_MAP = {
  xx: "XX" as const,
  xbc: "XBC" as const,
  xbrc: "XBRC" as const,
  bc: "BC" as const,
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

interface Props {
  dateRange: DateRangeFilter;
}

const INITIAL_POSITION_FILTERS = { ip: false, oop: false };
const INITIAL_BOARD_TYPE_FILTERS = {
  monotone: false,
  twoTone: false,
  rainbow: false,
};
const INITIAL_FLOP_ACTION_FILTERS = {
  xx: false,
  xbc: false,
  xbrc: false,
  bc: false,
};
const INITIAL_FLOP_RANK_TEXTURE_FILTERS = {
  trips: false,
  paired: false,
  unpaired: false,
};
const INITIAL_TURN_ACTION_FILTERS = {
  xx: false,
  xbc: false,
  xbrc: false,
  bc: false,
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

export const RiverView = ({ dateRange }: Props) => {
  const [riverStats, setRiverStats] = useState<RiverStats>();
  const [positionFilters, togglePosition, heroInPosition] = useToggleFilter(
    INITIAL_POSITION_FILTERS,
    POSITION_MAP,
  );
  const [boardTypeFilters, toggleBoard, boardTypes] = useToggleFilter(
    INITIAL_BOARD_TYPE_FILTERS,
    BOARD_TYPE_MAP,
  );
  const [flopActionFilters, toggleFlopAction, flopActions] = useToggleFilter(
    INITIAL_FLOP_ACTION_FILTERS,
    FLOP_ACTION_MAP,
  );
  const [flopRankTextureFilters, toggleFlopRankTexture, flopRankTextures] =
    useToggleFilter(INITIAL_FLOP_RANK_TEXTURE_FILTERS, FLOP_RANK_TEXTURE_MAP);
  const [turnActionFilters, toggleTurnAction, turnActions] = useToggleFilter(
    INITIAL_TURN_ACTION_FILTERS,
    TURN_ACTION_MAP,
  );
  const [turnRunoutFilters, toggleTurnRunout, turnRunouts] = useToggleFilter(
    INITIAL_TURN_RUNOUT_FILTERS,
    TURN_RUNOUT_MAP,
  );
  const [riverRunoutFilters, toggleRiverRunout, riverRunouts] = useToggleFilter(
    INITIAL_RIVER_RUNOUT_FILTERS,
    RIVER_RUNOUT_MAP,
  );

  useEffect(() => {
    const fetchStats = async () => {
      const stats = await getRiverStats(
        heroInPosition,
        boardTypes,
        [],
        flopActions,
        flopRankTextures,
        turnRunouts,
        turnActions,
        riverRunouts,
        dateRange.startDate,
        dateRange.endDate,
      );
      setRiverStats(stats);
    };

    fetchStats();
  }, [
    heroInPosition,
    boardTypes,
    flopActions,
    flopRankTextures,
    turnActions,
    turnRunouts,
    riverRunouts,
    dateRange.startDate,
    dateRange.endDate,
  ]);

  return (
    <div className="p-8 h-full content-start flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            General
          </span>
          <div className="flex flex-wrap gap-4">
            <FilterGroup
              options={positionOptions(positionFilters)}
              onToggle={togglePosition}
            />
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            Flop
          </span>
          <div className="flex flex-wrap gap-4">
            <FilterGroup
              options={actionLineOptions(flopActionFilters)}
              onToggle={toggleFlopAction}
            />
            <FilterGroup
              options={boardTypeOptions(boardTypeFilters)}
              onToggle={toggleBoard}
            />
            <FilterGroup
              options={flopRankTextureOptions(flopRankTextureFilters)}
              onToggle={toggleFlopRankTexture}
            />
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            Turn
          </span>
          <div className="flex flex-wrap gap-4">
            <FilterGroup
              options={actionLineOptions(turnActionFilters)}
              onToggle={toggleTurnAction}
            />
            <FilterGroup
              options={turnRunoutOptions(turnRunoutFilters)}
              onToggle={toggleTurnRunout}
            />
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            River
          </span>
          <div className="flex flex-wrap gap-4">
            <FilterGroup
              options={turnRunoutOptions(riverRunoutFilters)}
              onToggle={toggleRiverRunout}
            />
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3 max-w-7xl">
        <RiverActionPanel stats={riverStats?.actions} />
        <ShowdownPanel showdown={riverStats?.showdown} />
        <AvgPotPanel avgPot={riverStats?.avg_pot} />
      </div>
    </div>
  );
};
