import type {
  BoardTypeFilter,
  PotTypeFilter,
  CbetStats,
  DailyVolumePoint,
  Ranges,
  TurnStatsMap,
  FlopActionLine,
  FlopRankTextureFilter,
  TurnRunoutFilter,
  TurnActionLine,
  RiverRunoutFilter,
  RiverStats,
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
  betSizeMin?: number,
  betSizeMax?: number,
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
  if (betSizeMin !== undefined) {
    params.append("bet_size_min", String(betSizeMin));
  }
  if (betSizeMax !== undefined) {
    params.append("bet_size_max", String(betSizeMax));
  }
  const response = await fetch(`http://localhost:8000/cbets?${params}`);
  return response.json();
};

export interface VillainBetSizesResponse {
  villain_bet_sizes: number[];
}

export const getVillainBetSizes = async (
  heroInPosition: boolean[],
  boardTypes: BoardTypeFilter[],
  potTypes: PotTypeFilter[],
  startDate?: string,
  endDate?: string,
): Promise<VillainBetSizesResponse> => {
  const params = new URLSearchParams();
  for (const value of heroInPosition) {
    params.append("hero_in_position", String(value));
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
  const response = await fetch(`http://localhost:8000/cbets/bet-sizes?${params}`);
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

export const getRiverStats = async (
  heroInPosition: boolean[],
  boardTypes: BoardTypeFilter[],
  potTypes: PotTypeFilter[],
  flopActions: FlopActionLine[],
  flopRankTextures: FlopRankTextureFilter[],
  turnRunouts: TurnRunoutFilter[],
  turnActionSequences: TurnActionLine[],
  riverRunouts: RiverRunoutFilter[],
  startDate?: string,
  endDate?: string,
): Promise<RiverStats> => {
  const params = new URLSearchParams();
  for (const value of heroInPosition) {
    params.append("hero_in_position", String(value));
  }
  for (const value of boardTypes) {
    params.append("board_types", value);
  }
  for (const value of potTypes) {
    params.append("pot_types", value);
  }
  for (const value of flopActions) {
    params.append("flop_actions", value);
  }
  for (const value of flopRankTextures) {
    params.append("flop_rank_textures", value);
  }
  for (const value of turnRunouts) {
    params.append("turn_runouts", value);
  }
  for (const value of turnActionSequences) {
    params.append("turn_action_sequences", value);
  }
  for (const value of riverRunouts) {
    params.append("river_runouts", value);
  }
  if (startDate) {
    params.append("start_date", startDate);
  }
  if (endDate) {
    params.append("end_date", endDate);
  }
  const response = await fetch(`http://localhost:8000/river?${params}`);
  return response.json();
};
