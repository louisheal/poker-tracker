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
  donk_bet_pct: number;
  fold_to_donk_pct: number;
  hand_count: number;
}

export type FlopActionLine = "XX" | "XBC" | "XBRC" | "BC";

export type TurnRunoutFilter = "OVERCARD" | "FLUSH_COMPLETING" | "PAIRED" | "OTHER";

export interface TurnRunoutFilters {
  overcard: boolean;
  flushCompleting: boolean;
  paired: boolean;
  other: boolean;
}

export interface TurnStats {
  hero_bet_pct: number;
  villain_fold_to_hero_bet_pct: number;
  villain_bet_pct: number;
  hero_fold_to_villain_bet_pct: number;
  hand_count: number;
}

export type TurnStatsMap = { [key in FlopActionLine]: TurnStats };

export interface DailyVolumePoint {
  date: string;
  count: number;
}

export interface DateRangeFilter {
  startDate?: string;
  endDate?: string;
}
