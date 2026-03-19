export interface Stats {
  folds: number;
  raises: number;
  calls: number;
}

export interface RangeHands {
  [handKey: string]: Stats;
}

export type RangeGroup = { [position: string]: RangeHands };

export type Ranges = { [potType: string]: RangeGroup };

export type BoardTypeFilter = "MONOTONE" | "TWO_TONE" | "RAINBOW";
export type PotTypeFilter = "SRP" | "THREE_BET" | "FOUR_BET";

export interface PositionFilters {
  ip: boolean;
  oop: boolean;
}

export interface BoardTypeFilters {
  monotone: boolean;
  twoTone: boolean;
  rainbow: boolean;
}

export interface PotTypeFilters {
  srp: boolean;
  threeBet: boolean;
  fourBet: boolean;
}

export interface CbetStats {
  cbet_pct: number;
  fcbet_pct: number;
  raise_to_cbet_pct: number;
  donk_bet_pct: number;
  fold_to_donk_pct: number;
  raise_to_donk_pct: number;
  hand_count: number;
}

export type FlopActionLine = "XX" | "XBC" | "XBRC" | "BC";

export type TurnRunoutFilter = "OVERCARD" | "FLUSH_COMPLETING" | "PAIRED" | "OTHER";

export type RiverRunoutFilter = "OVERCARD" | "FLUSH_COMPLETING" | "PAIRED" | "OTHER";

export type FlopRankTextureFilter = "TRIPS" | "PAIRED" | "UNPAIRED";

export type TurnActionLine = "XX" | "XBC" | "XBRC" | "BC";

export interface TurnRunoutFilters {
  overcard: boolean;
  flushCompleting: boolean;
  paired: boolean;
  other: boolean;
}

export interface RiverRunoutFilters {
  overcard: boolean;
  flushCompleting: boolean;
  paired: boolean;
  other: boolean;
}

export interface FlopRankTextureFilters {
  trips: boolean;
  paired: boolean;
  unpaired: boolean;
}

export interface TurnActionFilters {
  xx: boolean;
  xbc: boolean;
  xbrc: boolean;
  bc: boolean;
}

export interface TurnStats {
  hero_bet_pct: number;
  villain_fold_to_hero_bet_pct: number;
  villain_raise_to_hero_bet_pct: number;
  villain_bet_pct: number;
  hero_fold_to_villain_bet_pct: number;
  hero_raise_to_villain_bet_pct: number;
  hand_count: number;
}

export type TurnStatsMap = { [key in FlopActionLine]: TurnStats };

export type ShowdownType = "CHECK_CHECK" | "BET_CALL" | "RAISE_OCCURRED";

export interface RiverActionStats {
  hero_bet_pct: number;
  villain_fold_to_hero_bet_pct: number;
  villain_raise_to_hero_bet_pct: number;
  villain_bet_pct: number;
  hero_fold_to_villain_bet_pct: number;
  hero_raise_to_villain_bet_pct: number;
  hand_count: number;
}

export interface ShowdownStats {
  bb_per_hand: number;
  hand_count: number;
}

export type ShowdownStatsMap = { [key in FlopActionLine]: ShowdownStats };

export interface AvgPotStats {
  avg_pot_bb: number;
  hand_count: number;
}

export type AvgPotStatsMap = { [key in FlopActionLine]: AvgPotStats };

export interface RiverStats {
  actions: RiverActionStats;
  showdown: ShowdownStatsMap;
  avg_pot: AvgPotStatsMap;
}

export interface FlopActionFilters {
  xx: boolean;
  xbc: boolean;
  xbrc: boolean;
  bc: boolean;
}

export interface DailyVolumePoint {
  date: string;
  count: number;
}

export interface DateRangeFilter {
  startDate?: string;
  endDate?: string;
}
