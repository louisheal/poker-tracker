import type { SolverResult } from "@/models";
import type { ActionOption } from "../types";
import { HandGrid as SharedHandGrid } from "@/common/HandGrid";

/** Extract hex colour from Tailwind bg-[#xxxxxx] class */
function extractHex(colour: string): string {
  const m = colour.match(/#[0-9a-fA-F]{6}/);
  return m ? m[0] : "#888888";
}

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

        const ev = hand.evs[hand.bestAction] ?? 0;
        const counts = hand.actionCounts;
        const eqPct = (hand.equity * 100).toFixed(1);

        // If we have actionCounts, build gradient stops; otherwise fall back to solid
        if (counts) {
          const total = Object.values(counts).reduce((a, b) => a + b, 0);
          if (total > 0) {
            const stops = actionOptions
              .filter((opt) => (counts[opt.key] ?? 0) > 0)
              .map((opt) => ({
                color: extractHex(opt.colour),
                percent: ((counts[opt.key] ?? 0) / total) * 100,
              }));

            return {
              gradientStops: stops,
              onClick: () => onSelectHand(key),
              isSelected: key === selectedHand,
              title: `${key}: ${hand.bestAction} (EV ${ev >= 0 ? "+" : ""}${ev.toFixed(1)}) | Equity ${eqPct}%`,
            };
          }
        }

        // Fallback: solid colour
        const opt = actionOptions.find((a) => a.key === hand.bestAction);
        return {
          colour: opt?.colour ?? "bg-muted text-muted-foreground",
          onClick: () => onSelectHand(key),
          isSelected: key === selectedHand,
          title: `${key}: ${hand.bestAction} (EV ${ev >= 0 ? "+" : ""}${ev.toFixed(1)}) | Equity ${eqPct}%`,
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
