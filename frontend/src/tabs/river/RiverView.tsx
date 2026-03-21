import { getRiverStats } from "@/api";
import { FilterGroup } from "@/components/FilterGroup";
import { useToggleFilter } from "@/hooks/useToggleFilter";
import type { DateRangeFilter, RiverStats } from "@/models";
import { useEffect, useState } from "react";
import { RiverActionPanel } from "./components/RiverActionPanel";
import { ShowdownPanel } from "./components/ShowdownPanel";
import { AvgPotPanel } from "./components/AvgPotPanel";

const POSITION_MAP = { ip: true as const, oop: false as const };
const BOARD_TYPE_MAP = { monotone: "MONOTONE" as const, twoTone: "TWO_TONE" as const, rainbow: "RAINBOW" as const };
const FLOP_ACTION_MAP = { xx: "XX" as const, xbc: "XBC" as const, xbrc: "XBRC" as const, bc: "BC" as const };
const FLOP_RANK_TEXTURE_MAP = { trips: "TRIPS" as const, paired: "PAIRED" as const, unpaired: "UNPAIRED" as const };
const TURN_ACTION_MAP = { xx: "XX" as const, xbc: "XBC" as const, xbrc: "XBRC" as const, bc: "BC" as const };
const TURN_RUNOUT_MAP = { overcard: "OVERCARD" as const, flushCompleting: "FLUSH_COMPLETING" as const, paired: "PAIRED" as const, other: "OTHER" as const };
const RIVER_RUNOUT_MAP = { overcard: "OVERCARD" as const, flushCompleting: "FLUSH_COMPLETING" as const, paired: "PAIRED" as const, other: "OTHER" as const };

interface Props {
  dateRange: DateRangeFilter;
}

export const RiverView = ({ dateRange }: Props) => {
  const [riverStats, setRiverStats] = useState<RiverStats>();
  const [positionFilters, togglePosition, heroInPosition] = useToggleFilter({ ip: false, oop: false }, POSITION_MAP);
  const [boardTypeFilters, toggleBoard, boardTypes] = useToggleFilter({ monotone: false, twoTone: false, rainbow: false }, BOARD_TYPE_MAP);
  const [flopActionFilters, toggleFlopAction, flopActions] = useToggleFilter({ xx: false, xbc: false, xbrc: false, bc: false }, FLOP_ACTION_MAP);
  const [flopRankTextureFilters, toggleFlopRankTexture, flopRankTextures] = useToggleFilter({ trips: false, paired: false, unpaired: false }, FLOP_RANK_TEXTURE_MAP);
  const [turnActionFilters, toggleTurnAction, turnActions] = useToggleFilter({ xx: false, xbc: false, xbrc: false, bc: false }, TURN_ACTION_MAP);
  const [turnRunoutFilters, toggleTurnRunout, turnRunouts] = useToggleFilter({ overcard: false, flushCompleting: false, paired: false, other: false }, TURN_RUNOUT_MAP);
  const [riverRunoutFilters, toggleRiverRunout, riverRunouts] = useToggleFilter({ overcard: false, flushCompleting: false, paired: false, other: false }, RIVER_RUNOUT_MAP);

  useEffect(() => {
    getRiverStats(
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
    ).then((stats) => {
      setRiverStats(stats);
    });
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
              options={[
                { key: "ip", label: "IP", active: positionFilters.ip },
                { key: "oop", label: "OOP", active: positionFilters.oop },
              ]}
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
              options={[
                { key: "xx", label: "XX", active: flopActionFilters.xx },
                { key: "xbc", label: "XBC", active: flopActionFilters.xbc },
                { key: "xbrc", label: "XBRC", active: flopActionFilters.xbrc },
                { key: "bc", label: "BC", active: flopActionFilters.bc },
              ]}
              onToggle={toggleFlopAction}
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
                {
                  key: "trips",
                  label: "TRIPS",
                  active: flopRankTextureFilters.trips,
                },
                {
                  key: "paired",
                  label: "PAIRED",
                  active: flopRankTextureFilters.paired,
                },
                {
                  key: "unpaired",
                  label: "UNPAIRED",
                  active: flopRankTextureFilters.unpaired,
                },
              ]}
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
              options={[
                { key: "xx", label: "XX", active: turnActionFilters.xx },
                { key: "xbc", label: "XBC", active: turnActionFilters.xbc },
                {
                  key: "xbrc",
                  label: "XBRC",
                  active: turnActionFilters.xbrc,
                },
                { key: "bc", label: "BC", active: turnActionFilters.bc },
              ]}
              onToggle={toggleTurnAction}
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
              options={[
                {
                  key: "overcard",
                  label: "OVERCARD",
                  active: riverRunoutFilters.overcard,
                },
                {
                  key: "flushCompleting",
                  label: "FLUSH",
                  active: riverRunoutFilters.flushCompleting,
                },
                {
                  key: "paired",
                  label: "PAIRED",
                  active: riverRunoutFilters.paired,
                },
                {
                  key: "other",
                  label: "OTHER",
                  active: riverRunoutFilters.other,
                },
              ]}
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
