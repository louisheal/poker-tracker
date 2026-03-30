import type { CardJson } from "@/api";

export const POSITIONS = ["LJ", "HJ", "CO", "BTN", "SB", "BB"] as const;
export type Position = (typeof POSITIONS)[number];

export const POSTFLOP_POSITION_ORDER: Position[] = [
  "SB",
  "BB",
  "LJ",
  "HJ",
  "CO",
  "BTN",
];

export interface ActionOption {
  key: string;
  label: string;
  colour: string;
}

// Colours match the ranges grid palette:
//   Fold  = blue  (#3c78fa)
//   Check/Call = green (#22c55e)
//   Bet/Raise  = red family (#ef4444 - #991b1b)

export const PREFLOP_ACTIONS: ActionOption[] = [
  { key: "Fold", label: "Fold", colour: "bg-[#3c78fa] text-white" },
  { key: "Call", label: "Call", colour: "bg-[#22c55e] text-white" },
  { key: "Raise", label: "Raise", colour: "bg-[#ef4444] text-white" },
];

export const PREFLOP_BB_CHECK_ACTIONS: ActionOption[] = [
  { key: "Check", label: "Check", colour: "bg-[#22c55e] text-white" },
  { key: "Raise", label: "Raise", colour: "bg-[#ef4444] text-white" },
];

export const POSTFLOP_OPEN_ACTIONS: ActionOption[] = [
  { key: "Check", label: "Check", colour: "bg-[#22c55e] text-white" },
  { key: "B33", label: "Bet 33%", colour: "bg-[#f87171] text-white" },
  { key: "B50", label: "Bet 50%", colour: "bg-[#ef4444] text-white" },
  { key: "B66", label: "Bet 66%", colour: "bg-[#ef4444] text-white" },
  { key: "B100", label: "Bet 100%", colour: "bg-[#dc2626] text-white" },
  { key: "B133", label: "Bet 133%", colour: "bg-[#b91c1c] text-white" },
  { key: "B200", label: "Bet 200%", colour: "bg-[#991b1b] text-white" },
];

export const POSTFLOP_FACING_BET_ACTIONS: ActionOption[] = [
  { key: "Fold", label: "Fold", colour: "bg-[#3c78fa] text-white" },
  { key: "Call", label: "Call", colour: "bg-[#22c55e] text-white" },
  { key: "R3x", label: "Raise 3x", colour: "bg-[#ef4444] text-white" },
  { key: "R4x", label: "Raise 4x", colour: "bg-[#dc2626] text-white" },
  { key: "R5x", label: "Raise 5x", colour: "bg-[#b91c1c] text-white" },
];

export interface ActionTile {
  type: "action";
  id: string;
  label: string;
  sublabel?: string;
  options: ActionOption[];
  selected: string | null;
  section: "preflop" | "flop" | "turn" | "river";
  actionIndex: number;
}

export interface BoardTile {
  type: "board";
  id: string;
  street: "flop" | "turn" | "river";
  requiredCards: number;
  cards: CardJson[];
  complete: boolean;
}

export type Tile = ActionTile | BoardTile;

export interface SolverSpot {
  preflopActions: string[];
  flopCards: CardJson[];
  flopActions: string[];
  turnCard: CardJson | null;
  turnActions: string[];
  riverCard: CardJson | null;
  riverActions: string[];
}

export const INITIAL_SPOT: SolverSpot = {
  preflopActions: [],
  flopCards: [],
  flopActions: [],
  turnCard: null,
  turnActions: [],
  riverCard: null,
  riverActions: [],
};
