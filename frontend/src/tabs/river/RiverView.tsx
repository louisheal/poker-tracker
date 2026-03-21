import { getRiverStats } from "@/api";
import { FilterGroup } from "@/components/FilterGroup";
import { useMemo } from "react";
import type {
  BoardTypeFilter,
  PositionFilters,
  BoardTypeFilters,
  DateRangeFilter,
  FlopActionFilters,
  FlopActionLine,
  FlopRankTextureFilter,
  FlopRankTextureFilters,
  TurnRunoutFilters,
  TurnRunoutFilter,
  TurnActionFilters,
  TurnActionLine,
  RiverRunoutFilter,
  RiverRunoutFilters,
} from "@/models";
import { useEffect, useState } from "react";
import type { RiverStats } from "@/models";
import { RiverActionPanel } from "./components/RiverActionPanel";
import { ShowdownPanel } from "./components/ShowdownPanel";
import { AvgPotPanel } from "./components/AvgPotPanel";

const INITIAL_POSITION_FILTERS: PositionFilters = { ip: false, oop: false };

const INITIAL_BOARD_TYPE_FILTERS: BoardTypeFilters = {
  monotone: false,
  twoTone: false,
  rainbow: false,
};

const INITIAL_FLOP_ACTION_FILTERS: FlopActionFilters = {
  xx: false,
  xbc: false,
  xbrc: false,
  bc: false,
};

const INITIAL_FLOP_RANK_TEXTURE_FILTERS: FlopRankTextureFilters = {
  trips: false,
  paired: false,
  unpaired: false,
};

const INITIAL_TURN_ACTION_FILTERS: TurnActionFilters = {
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

const INITIAL_RIVER_RUNOUT_FILTERS: RiverRunoutFilters = {
  overcard: false,
  flushCompleting: false,
  paired: false,
  other: false,
};

interface Props {
  dateRange: DateRangeFilter;
}

export const RiverView = ({ dateRange }: Props) => {
  const [riverStats, setRiverStats] = useState<RiverStats>();
  const [positionFilters, setPositionFilters] = useState<PositionFilters>(
    INITIAL_POSITION_FILTERS,
  );
  const [boardTypeFilters, setBoardTypeFilters] = useState<BoardTypeFilters>(
    INITIAL_BOARD_TYPE_FILTERS,
  );
  const [flopActionFilters, setFlopActionFilters] =
    useState<FlopActionFilters>(INITIAL_FLOP_ACTION_FILTERS);
  const [flopRankTextureFilters, setFlopRankTextureFilters] =
    useState<FlopRankTextureFilters>(INITIAL_FLOP_RANK_TEXTURE_FILTERS);
  const [turnActionFilters, setTurnActionFilters] =
    useState<TurnActionFilters>(INITIAL_TURN_ACTION_FILTERS);
  const [turnRunoutFilters, setTurnRunoutFilters] =
    useState<TurnRunoutFilters>(INITIAL_TURN_RUNOUT_FILTERS);
  const [riverRunoutFilters, setRiverRunoutFilters] =
    useState<RiverRunoutFilters>(INITIAL_RIVER_RUNOUT_FILTERS);

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

  const toggleFlopActionFilter = (key: string) => {
    setFlopActionFilters((prev) => ({
      ...prev,
      [key as keyof FlopActionFilters]: !prev[key as keyof FlopActionFilters],
    }));
  };

  const toggleFlopRankTextureFilter = (key: string) => {
    setFlopRankTextureFilters((prev) => ({
      ...prev,
      [key as keyof FlopRankTextureFilters]:
        !prev[key as keyof FlopRankTextureFilters],
    }));
  };

  const toggleTurnActionFilter = (key: string) => {
    setTurnActionFilters((prev) => ({
      ...prev,
      [key as keyof TurnActionFilters]: !prev[key as keyof TurnActionFilters],
    }));
  };

  const toggleTurnRunoutFilter = (key: string) => {
    setTurnRunoutFilters((prev) => ({
      ...prev,
      [key as keyof TurnRunoutFilters]: !prev[key as keyof TurnRunoutFilters],
    }));
  };

  const toggleRiverRunoutFilter = (key: string) => {
    setRiverRunoutFilters((prev) => ({
      ...prev,
      [key as keyof RiverRunoutFilters]:
        !prev[key as keyof RiverRunoutFilters],
    }));
  };

  const {
    heroInPosition,
    boardTypes,
    flopActions,
    flopRankTextures,
    turnActions,
    turnRunouts,
    riverRunouts,
  } = useMemo(() => {
    const heroInPosition: boolean[] = [];
    const boardTypes: BoardTypeFilter[] = [];
    const flopActions: FlopActionLine[] = [];
    const flopRankTextures: FlopRankTextureFilter[] = [];
    const turnActions: TurnActionLine[] = [];
    const turnRunouts: TurnRunoutFilter[] = [];
    const riverRunouts: RiverRunoutFilter[] = [];

    if (positionFilters.ip) heroInPosition.push(true);
    if (positionFilters.oop) heroInPosition.push(false);

    if (boardTypeFilters.monotone) boardTypes.push("MONOTONE");
    if (boardTypeFilters.twoTone) boardTypes.push("TWO_TONE");
    if (boardTypeFilters.rainbow) boardTypes.push("RAINBOW");

    if (flopActionFilters.xx) flopActions.push("XX");
    if (flopActionFilters.xbc) flopActions.push("XBC");
    if (flopActionFilters.xbrc) flopActions.push("XBRC");
    if (flopActionFilters.bc) flopActions.push("BC");

    if (flopRankTextureFilters.trips) flopRankTextures.push("TRIPS");
    if (flopRankTextureFilters.paired) flopRankTextures.push("PAIRED");
    if (flopRankTextureFilters.unpaired) flopRankTextures.push("UNPAIRED");

    if (turnActionFilters.xx) turnActions.push("XX");
    if (turnActionFilters.xbc) turnActions.push("XBC");
    if (turnActionFilters.xbrc) turnActions.push("XBRC");
    if (turnActionFilters.bc) turnActions.push("BC");

    if (turnRunoutFilters.overcard) turnRunouts.push("OVERCARD");
    if (turnRunoutFilters.flushCompleting)
      turnRunouts.push("FLUSH_COMPLETING");
    if (turnRunoutFilters.paired) turnRunouts.push("PAIRED");
    if (turnRunoutFilters.other) turnRunouts.push("OTHER");

    if (riverRunoutFilters.overcard) riverRunouts.push("OVERCARD");
    if (riverRunoutFilters.flushCompleting)
      riverRunouts.push("FLUSH_COMPLETING");
    if (riverRunoutFilters.paired) riverRunouts.push("PAIRED");
    if (riverRunoutFilters.other) riverRunouts.push("OTHER");

    return {
      heroInPosition,
      boardTypes,
      flopActions,
      flopRankTextures,
      turnActions,
      turnRunouts,
      riverRunouts,
    };
  }, [
    positionFilters,
    boardTypeFilters,
    flopActionFilters,
    flopRankTextureFilters,
    turnActionFilters,
    turnRunoutFilters,
    riverRunoutFilters,
  ]);

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
              onToggle={togglePositionFilter}
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
              onToggle={toggleFlopActionFilter}
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
              onToggle={toggleFlopRankTextureFilter}
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
              onToggle={toggleTurnActionFilter}
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
              onToggle={toggleRiverRunoutFilter}
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
