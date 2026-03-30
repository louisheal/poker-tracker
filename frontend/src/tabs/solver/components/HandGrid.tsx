import type { SolverResult } from "@/models";
import type { ActionOption } from "../types";
import { HandGrid as SharedHandGrid } from "@/common/HandGrid";

interface Props {
  result: SolverResult;
  selectedHand: string | null;
  actionOptions: ActionOption[];
  onSelectHand: (handKey: string) => void;
}

export const HandGrid = ({
  result,
  selectedHand,
  actionOptions,
  onSelectHand,
}: Props) => (
  <div className="space-y-1.5">
    <div className="flex items-center justify-between">
      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Hand Grid
      </span>
      <span className="text-xs text-muted-foreground">
        {result.totalHands} hands
      </span>
    </div>

    <SharedHandGrid
      cellProps={(key) => {
        const hand = result.hands[key];
        if (!hand) return {};
        const opt = actionOptions.find((a) => a.key === hand.bestAction);
        const ev = hand.evs[hand.bestAction] ?? 0;
        return {
          colour: opt?.colour ?? "bg-muted text-muted-foreground",
          onClick: () => onSelectHand(key),
          isSelected: key === selectedHand,
          title: `${key}: ${hand.bestAction} (EV ${ev >= 0 ? "+" : ""}${ev.toFixed(1)})`,
        };
      }}
    />

    <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
      <span>Diagonal = pairs</span>
      <span>Above = suited</span>
      <span>Below = offsuit</span>
    </div>
  </div>
);
