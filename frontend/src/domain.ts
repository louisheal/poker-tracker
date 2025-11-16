export interface HandDto {
  Id: string;
  FstCard: Card;
  SndCard: Card;
}

export interface Card {
  Suit: Suit;
  Rank: Rank;
}

export type Rank =
  | "2"
  | "3"
  | "4"
  | "5"
  | "6"
  | "7"
  | "8"
  | "9"
  | "T"
  | "J"
  | "Q"
  | "K"
  | "A";

export type Suit = "H" | "D" | "S" | "C";

export interface HandData {
  key: string;
  folds: number;
  raises: number;
}

export interface Ranges {
  played: HandData[][];
  gto: HandData[][];
}
