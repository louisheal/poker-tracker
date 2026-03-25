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

export type TurnRunoutFilter =
  | "OVERCARD"
  | "FLUSH_COMPLETING"
  | "PAIRED"
  | "OTHER";

export type RiverRunoutFilter =
  | "OVERCARD"
  | "FLUSH_COMPLETING"
  | "PAIRED"
  | "OTHER";

export type FlopRankTextureFilter = "TRIPS" | "PAIRED" | "UNPAIRED";

export type TurnActionLine = "XX" | "XBC" | "XBRC" | "BC";

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

export interface DailyVolumePoint {
  date: string;
  count: number;
}

export interface DateRangeFilter {
  startDate?: string;
  endDate?: string;
}

// --- Flop Anchor Types ---

export interface ActionLine {
  actions: LineActionItem[];
  cursor: number;
}

export interface LineActionItem {
  actor: "hero" | "villain" | "marker";
  action: string;
  sizeRange?: [number, number];
  label: string;
}

export interface FlopStreetStats {
  cbet_pct: number;
  fold_to_cbet_pct: number;
  raise_to_cbet_pct: number;
  fold_to_cbet_raise_pct: number;
  donk_bet_pct: number;
  fold_to_donk_pct: number;
  raise_to_donk_pct: number;
  fold_to_donk_raise_pct: number;
}

export interface TurnStreetStats {
  hero_bet_pct: number;
  villain_fold_to_hero_bet_pct: number;
  villain_raise_to_hero_bet_pct: number;
  villain_bet_pct: number;
  hero_fold_to_villain_bet_pct: number;
  hero_raise_to_villain_bet_pct: number;
}

export type MadeHandType =
  | "STRAIGHT_FLUSH"
  | "QUADS"
  | "FULL_HOUSE"
  | "FLUSH"
  | "STRAIGHT"
  | "SET"
  | "TWO_PAIR"
  | "OVERPAIR"
  | "TOP_PAIR"
  | "PAIR"
  | "ACE_HIGH"
  | "NO_MADE_HAND";

export type DrawType =
  | "FLUSH_OESD"
  | "FLUSH_GUTSHOT"
  | "FLUSH_DRAW"
  | "OESD"
  | "GUTSHOT"
  | "NO_DRAW";

export interface PlayerHandTypes {
  made_hands: Record<MadeHandType, number>;
  draws: Record<DrawType, number>;
}

export interface HandTypeDistributionResponse {
  hero: PlayerHandTypes;
  villain: PlayerHandTypes;
}
