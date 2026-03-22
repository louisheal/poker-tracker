import type { CardJson } from "@/api";

const SUIT_SYMBOLS: Record<string, string> = {
  H: "♥",
  D: "♦",
  S: "♠",
  C: "♣",
};

const SUIT_COLORS: Record<string, string> = {
  H: "text-red-400",
  D: "text-blue-400",
  S: "text-white",
  C: "text-green-500",
};

interface Props {
  card: CardJson;
}

export const PlayingCard = ({ card }: Props) => {
  const symbol = SUIT_SYMBOLS[card.Suit] ?? card.Suit;
  const color = SUIT_COLORS[card.Suit] ?? "text-foreground";

  return (
    <span
      className={`inline-flex items-center justify-center rounded border border-border bg-background px-1 py-0.5 text-xs font-mono font-semibold ${color}`}
    >
      {card.Rank}
      {symbol}
    </span>
  );
};
