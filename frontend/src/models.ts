export interface Stats {
  folds: number;
  raises: number;
}

export interface RangeHands {
  [handKey: string]: Stats;
}

export type RfiRanges = { [position: string]: RangeHands };
