export interface Stats {
  folds: number;
  raises: number;
}

export interface RangeHands {
  hands: { [handKey: string]: Stats };
}

export type RangeResponse = { [position: string]: RangeHands };
