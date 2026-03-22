import type { NextAction } from "@/api";
import { EvRow } from "./EvRow";

const ACTION_LABELS: Record<string, string> = {
  X: "Check",
  B: "Bet",
  C: "Call",
  R: "Raise",
  F: "Fold",
};

const BET_ACTION_LABELS: Record<string, string> = {
  "B0-50": "Bet Small (0-50%)",
  "B50-100": "Bet Medium (50-100%)",
  "B100-200": "Bet Large (100-200%)",
  "B200+": "Bet Overbet (200%+)",
  "R0-50": "Raise Small (0-50%)",
  "R50-100": "Raise Medium (50-100%)",
  "R100-200": "Raise Large (100-200%)",
  "R200+": "Raise Overbet (200%+)",
};

function getActionLabel(action: string): string {
  return BET_ACTION_LABELS[action] || ACTION_LABELS[action] || action;
}

function parseActionKey(action: string): {
  base: string;
  sizeRange?: [number, number];
} {
  const match = action.match(/^([BRCXF])(\d+-\d+|\d+\+)?$/);
  if (!match) return { base: action };
  const base = match[1];
  const sizePart = match[2];
  if (!sizePart) return { base };
  if (sizePart.endsWith("+")) {
    const lo = parseInt(sizePart.slice(0, -1));
    return { base, sizeRange: [lo, 999] };
  }
  const [lo, hi] = sizePart.split("-").map(Number);
  return { base, sizeRange: [lo, hi] };
}

interface Props {
  nextActor: "hero" | "villain" | "";
  overallEv: number;
  handCount: number;
  nextActions: NextAction[];
  onActionClick: (action: string, sizeRange?: [number, number]) => void;
  showTurnTransition?: boolean;
  onContinueToTurn?: () => void;
  showRiverTransition?: boolean;
  onContinueToRiver?: () => void;
}

export const EvPanel = ({
  nextActor,
  overallEv,
  handCount,
  nextActions,
  onActionClick,
  showTurnTransition,
  onContinueToTurn,
  showRiverTransition,
  onContinueToRiver,
}: Props) => {
  const actorLabel = nextActor === "hero" ? "Hero" : "Villain";
  const overallColor =
    overallEv > 0
      ? "text-emerald-400"
      : overallEv < 0
        ? "text-red-400"
        : "text-muted-foreground";

  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-4">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Expected Value
        </h3>
        <span className="text-xs text-muted-foreground">{handCount} hands</span>
      </div>

      {/* Overall EV */}
      <div className="bg-background/50 border border-border rounded-lg px-4 py-3 flex items-center justify-between">
        <span className="text-sm font-semibold">Overall</span>
        <span className={`text-lg font-bold tabular-nums ${overallColor}`}>
          {overallEv > 0 ? "+" : ""}
          {overallEv.toFixed(1)} BB
        </span>
      </div>

      {/* Dynamic per-action EV */}
      <div className="flex flex-col divide-y divide-border">
        {nextActions.map((na) => {
          const { base, sizeRange } = parseActionKey(na.action);
          return (
            <EvRow
              key={na.action}
              label={`${actorLabel} ${getActionLabel(na.action)}`}
              evBb={na.ev}
              count={na.count}
              onClick={() => onActionClick(base, sizeRange)}
            />
          );
        })}
        {nextActions.length === 0 && showTurnTransition && (
          <button
            onClick={onContinueToTurn}
            className="text-sm font-medium text-primary hover:underline py-2 text-left"
          >
            Continue to Turn →
          </button>
        )}
        {nextActions.length === 0 && showRiverTransition && (
          <button
            onClick={onContinueToRiver}
            className="text-sm font-medium text-primary hover:underline py-2 text-left"
          >
            Continue to River →
          </button>
        )}
        {nextActions.length === 0 && !showTurnTransition && !showRiverTransition && (
          <p className="text-xs text-muted-foreground py-2">
            No further actions (hand complete)
          </p>
        )}
      </div>
    </div>
  );
};
