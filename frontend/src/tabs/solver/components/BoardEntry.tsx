import { useState } from "react";
import { createPortal } from "react-dom";
import type { CardJson } from "@/api";
import { PlayingCard } from "@/components/PlayingCard";
import { CardPicker } from "./CardPicker";

interface Props {
  street: "flop" | "turn" | "river";
  requiredCards: number;
  cards: CardJson[];
  allUsedCards: CardJson[];
  onCardsChange: (cards: CardJson[]) => void;
}

const STREET_LABELS: Record<string, string> = {
  flop: "Flop",
  turn: "Turn",
  river: "River",
};

export const BoardEntry = ({
  street,
  requiredCards,
  cards,
  allUsedCards,
  onCardsChange,
}: Props) => {
  const [showPicker, setShowPicker] = useState(false);

  const handlePick = (card: CardJson) => {
    const next = [...cards, card];
    onCardsChange(next);
    if (next.length >= requiredCards) {
      setShowPicker(false);
    }
  };

  const handleSlotClick = (index: number) => {
    if (index < cards.length) {
      onCardsChange(cards.slice(0, index));
    } else if (index === cards.length) {
      setShowPicker((prev) => !prev);
    }
  };

  const slots = Array.from(
    { length: requiredCards },
    (_, i) => cards[i] ?? null,
  );
  const isComplete = cards.length >= requiredCards;

  return (
    <div className="shrink-0">
      <div
        className={`flex flex-col gap-1 rounded-lg border p-2 min-w-[80px] ${
          isComplete
            ? "border-border bg-card/60"
            : "border-primary/60 bg-card ring-1 ring-primary/30"
        }`}
      >
        <div className="text-[11px] font-semibold text-foreground text-center">
          {STREET_LABELS[street]}
        </div>
        <div className="flex gap-1 justify-center">
          {slots.map((card, i) => (
            <button
              key={i}
              onClick={() => handleSlotClick(i)}
              className="w-8 h-10 rounded border border-dashed border-muted-foreground/40 flex items-center justify-center hover:border-foreground/50 transition-colors"
            >
              {card ? (
                <PlayingCard card={card} />
              ) : (
                <span className="text-muted-foreground/40 text-xs">+</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {showPicker &&
        !isComplete &&
        createPortal(
          <div
            className="fixed inset-0 z-50 flex items-center justify-center"
            onClick={() => setShowPicker(false)}
          >
            <div className="absolute inset-0 bg-black/50" />
            <div
              className="relative p-4 rounded-xl border border-border bg-card shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-foreground">
                  Pick {STREET_LABELS[street].toLowerCase()} card{" "}
                  {cards.length + 1}
                  {requiredCards > 1 ? ` of ${requiredCards}` : ""}
                </span>
                <button
                  onClick={() => setShowPicker(false)}
                  className="text-xs text-muted-foreground hover:text-foreground px-2 py-1"
                >
                  Close
                </button>
              </div>
              <CardPicker
                selectedCards={allUsedCards}
                onSelectCard={handlePick}
              />
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
};
