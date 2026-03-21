import { getTurnStats } from "@/api";
import { FilterGroup } from "@/components/FilterGroup";
import type {
  TurnStats,
  DateRangeFilter,
  FlopActionLine,
} from "@/models";
import { useEffect, useState } from "react";
import { useToggleFilter } from "@/hooks/useToggleFilter";
import { TurnStatsPanel } from "./components/TurnStatsPanel";

const POSITION_MAP = { ip: true as const, oop: false as const };
const BOARD_TYPE_MAP = { monotone: "MONOTONE" as const, twoTone: "TWO_TONE" as const, rainbow: "RAINBOW" as const };
const POT_TYPE_MAP = { srp: "SRP" as const, threeBet: "THREE_BET" as const, fourBet: "FOUR_BET" as const };
const TURN_RUNOUT_MAP = { overcard: "OVERCARD" as const, flushCompleting: "FLUSH_COMPLETING" as const, paired: "PAIRED" as const, other: "OTHER" as const };

const FLOP_ACTION_LINES: FlopActionLine[] = ["XX", "XBC", "XBRC", "BC"];

interface Props {
  dateRange: DateRangeFilter;
}

export const TurnView = ({ dateRange }: Props) => {
  const [positionFilters, togglePosition, heroInPosition] = useToggleFilter(
    { ip: false, oop: false }, POSITION_MAP,
  );
  const [boardTypeFilters, toggleBoard, boardTypes] = useToggleFilter(
    { monotone: false, twoTone: false, rainbow: false }, BOARD_TYPE_MAP,
  );
  const [potTypeFilters, togglePot, potTypes] = useToggleFilter(
    { srp: false, threeBet: false, fourBet: false }, POT_TYPE_MAP,
  );
  const [turnRunoutFilters, toggleTurnRunout, turnRunouts] = useToggleFilter(
    { overcard: false, flushCompleting: false, paired: false, other: false }, TURN_RUNOUT_MAP,
  );

  const [turnStats, setTurnStats] = useState<
    { [key in FlopActionLine]: TurnStats | undefined }
  >({
    XX: undefined,
    XBC: undefined,
    XBRC: undefined,
    BC: undefined,
  });

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

      <div className="grid gap-4 md:grid-cols-2 max-w-5xl">
        {FLOP_ACTION_LINES.map((line) => (
          <TurnStatsPanel key={line} title={line} stats={turnStats[line]} />
        ))}
      </div>
    </div>
  );
};
