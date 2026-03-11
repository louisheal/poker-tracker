import type {
  BoardTypeFilter,
  PotTypeFilter,
  CbetStats,
  DailyVolumePoint,
  Ranges,
  TurnStatsMap,
  FlopActionLine,
  TurnRunoutFilter,
} from "./models";

export const getRanges = async (startDate?: string, endDate?: string) => {
  const params = new URLSearchParams();
  if (startDate) {
    params.append("start_date", startDate);
  }
  if (endDate) {
    params.append("end_date", endDate);
  }
  const query = params.toString();
  const url = query
    ? `http://localhost:8000?${query}`
    : "http://localhost:8000";
  const response = await fetch(url);
  const rangeResponse: Ranges = await response.json();
  return rangeResponse;
};

export const getCbets = async (
  heroInPosition: boolean[],
  heroPfr: boolean[],
  boardTypes: BoardTypeFilter[],
  potTypes: PotTypeFilter[],
  startDate?: string,
  endDate?: string,
): Promise<CbetStats> => {
  const params = new URLSearchParams();
  for (const value of heroInPosition) {
    params.append("hero_in_position", String(value));
  }
  for (const value of heroPfr) {
    params.append("hero_preflop_raiser", String(value));
  }
  for (const value of boardTypes) {
    params.append("board_types", value);
  }
  for (const value of potTypes) {
    params.append("pot_types", value);
  }
  if (startDate) {
    params.append("start_date", startDate);
  }
  if (endDate) {
    params.append("end_date", endDate);
  }
  const response = await fetch(`http://localhost:8000/cbets?${params}`);
  return response.json();
};

export const getHandVolume = async (
  startDate?: string,
  endDate?: string,
): Promise<DailyVolumePoint[]> => {
  const params = new URLSearchParams();
  if (startDate) {
    params.append("start_date", startDate);
  }
  if (endDate) {
    params.append("end_date", endDate);
  }
  const query = params.toString();
  const url = query
    ? `http://localhost:8000/hands/volume?${query}`
    : "http://localhost:8000/hands/volume";
  const response = await fetch(url);
  return response.json();
};

export const getTurnStats = async (
  heroInPosition: boolean[],
  heroPfr: boolean[],
  boardTypes: BoardTypeFilter[],
  potTypes: PotTypeFilter[],
  turnRunouts: TurnRunoutFilter[],
  startDate?: string,
  endDate?: string,
): Promise<TurnStatsMap> => {
  const params = new URLSearchParams();
  for (const value of heroInPosition) {
    params.append("hero_in_position", String(value));
  }
  for (const value of heroPfr) {
    params.append("hero_preflop_raiser", String(value));
  }
  for (const value of boardTypes) {
    params.append("board_types", value);
  }
  for (const value of potTypes) {
    params.append("pot_types", value);
  }
  for (const value of turnRunouts) {
    params.append("turn_runouts", value);
  }
  if (startDate) {
    params.append("start_date", startDate);
  }
  if (endDate) {
    params.append("end_date", endDate);
  }
  const response = await fetch(`http://localhost:8000/turn?${params}`);
  return response.json();
};
