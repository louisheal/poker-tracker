import type { CardJson } from "@/api";
import type { Tile } from "../types";
import { DecisionTile } from "./DecisionTile";
import { BoardEntry } from "./BoardEntry";

interface Props {
  tiles: Tile[];
  viewTileId: string | null;
  allBoardCards: CardJson[];
  onActionSelect: (tileId: string, action: string) => void;
  onBoardChange: (tileId: string, cards: CardJson[]) => void;
  onNavigate: (tileId: string) => void;
}

export const ActionSequence = ({
  tiles,
  viewTileId,
  allBoardCards,
  onActionSelect,
  onBoardChange,
  onNavigate,
}: Props) => (
  <div className="flex gap-1.5 overflow-x-auto pb-2 items-start">
    {tiles.map((tile) => {
      if (tile.type === "action") {
        return (
          <DecisionTile
            key={tile.id}
            label={tile.label}
            sublabel={tile.sublabel}
            options={tile.options}
            selected={tile.selected}
            isViewed={tile.id === viewTileId}
            onSelect={(action) => onActionSelect(tile.id, action)}
            onNavigate={() => onNavigate(tile.id)}
          />
        );
      }
      return (
        <BoardEntry
          key={tile.id}
          street={tile.street}
          requiredCards={tile.requiredCards}
          cards={tile.cards}
          allUsedCards={allBoardCards}
          onCardsChange={(cards) => onBoardChange(tile.id, cards)}
        />
      );
    })}
    {tiles.length === 0 && (
      <div className="text-xs text-muted-foreground py-3">
        Build the action sequence from LJ onward
      </div>
    )}
  </div>
);
