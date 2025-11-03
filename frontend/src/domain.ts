export interface HandDto {
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

export type Suit = "Hearts" | "Diamonds" | "Spades" | "Clubs";
