import type { CardJson } from "@/api";
import { PlayingCard } from "@/components/PlayingCard";

const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];
const SUITS = ["S", "H", "D", "C"];

interface Props {
  selectedCards: CardJson[];
  onSelectCard: (card: CardJson) => void;
}

const isSelected = (card: CardJson, selected: CardJson[]) =>
  selected.some((c) => c.Rank === card.Rank && c.Suit === card.Suit);

export const CardPicker = ({ selectedCards, onSelectCard }: Props) => (
  <div className="grid grid-cols-13 gap-0.5">
    {SUITS.map((suit) =>
      RANKS.map((rank) => {
        const card: CardJson = { Rank: rank, Suit: suit };
        const disabled = isSelected(card, selectedCards);

        return (
          <button
            key={`${rank}${suit}`}
            onClick={() => onSelectCard(card)}
            disabled={disabled}
            className={`p-0.5 rounded transition-opacity ${disabled ? "opacity-20 cursor-not-allowed" : "hover:bg-accent/50 cursor-pointer"}`}
          >
            <PlayingCard card={card} />
          </button>
        );
      }),
    )}
  </div>
);
