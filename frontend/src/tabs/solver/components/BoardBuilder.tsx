import { useState } from "react";
import type { CardJson } from "@/api";
import { PlayingCard } from "@/components/PlayingCard";
import { CardPicker } from "./CardPicker";

interface Props {
  board: CardJson[];
  onBoardChange: (board: CardJson[]) => void;
}

const SLOT_LABELS = ["Flop", "Flop", "Flop", "Turn", "River"];
const MAX_BOARD_CARDS = 5;

export const BoardBuilder = ({ board, onBoardChange }: Props) => {
  const [showPicker, setShowPicker] = useState(false);

  const handleSelectCard = (card: CardJson) => {
    if (board.length >= MAX_BOARD_CARDS) return;
    const next = [...board, card];
    onBoardChange(next);
    if (next.length >= MAX_BOARD_CARDS) {
      setShowPicker(false);
    }
  };

  const handleRemoveCard = (index: number) => {
    // Remove this card and all cards after it
    onBoardChange(board.slice(0, index));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Board
        </span>

        <div className="flex items-center gap-1.5">
          {Array.from({ length: MAX_BOARD_CARDS }).map((_, i) => {
            const card = board[i];
            const slotLabel = SLOT_LABELS[i];
            const isFlop = i < 3;
            const showDivider = i === 3 || i === 4;

            return (
              <div key={i} className="flex items-center gap-1.5">
                {showDivider && board.length >= i && (
                  <div className="w-px h-6 bg-border mx-0.5" />
                )}
                {card ? (
                  <button
                    onClick={() => handleRemoveCard(i)}
                    className="hover:opacity-70 transition-opacity"
                    title={`Remove ${slotLabel}`}
                  >
                    <PlayingCard card={card} />
                  </button>
                ) : (
                  <button
                    onClick={() => setShowPicker(true)}
                    disabled={i !== board.length || (isFlop && i > 0 && board.length < i)}
                    className="w-7 h-8 rounded border border-dashed border-border text-[9px] text-muted-foreground flex items-center justify-center hover:border-foreground/50 hover:text-foreground/50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    {slotLabel[0]}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {board.length > 0 && (
          <button
            onClick={() => onBoardChange([])}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors ml-1"
          >
            Clear
          </button>
        )}
      </div>

      {showPicker && board.length < MAX_BOARD_CARDS && (
        <div className="p-3 rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted-foreground">
              Pick {board.length < 3 ? `flop card ${board.length + 1}` : board.length === 3 ? "turn card" : "river card"}
            </span>
            <button
              onClick={() => setShowPicker(false)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Close
            </button>
          </div>
          <CardPicker selectedCards={board} onSelectCard={handleSelectCard} />
        </div>
      )}
    </div>
  );
};
