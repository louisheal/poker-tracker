import type { SolverResult } from "@/models";
import type { ActionOption } from "../types";
import { ComboGrid } from "./ComboGrid";

interface Props {
  result: SolverResult;
  selectedHand: string | null;
  actionOptions: ActionOption[];
}

export const SolverResults = ({
  result,
  selectedHand,
  actionOptions,
}: Props) => {
  const handData = selectedHand ? result.hands[selectedHand] : null;

  return (
    <div className="space-y-4">
      {/* Selected hand detail + combo grid */}
      {handData && selectedHand && (
        <div className="p-3 rounded-lg border border-border bg-card space-y-3">
          <h4 className="text-sm font-medium text-foreground">
            {selectedHand}
          </h4>

          {/* Per-action EVs */}
          <div className="space-y-1">
            {actionOptions.map((opt) => {
              const ev = handData.evs[opt.key];
              if (ev === undefined) return null;
              const isBest = opt.key === handData.bestAction;
              return (
                <div key={opt.key} className="flex justify-between text-xs">
                  <span
                    className={
                      isBest
                        ? "text-foreground font-medium"
                        : "text-muted-foreground"
                    }
                  >
                    {isBest && "* "}
                    {opt.label}
                  </span>
                  <span
                    className={
                      ev >= 0 ? "text-emerald-400" : "text-red-400"
                    }
                  >
                    {ev >= 0 ? "+" : ""}
                    {ev.toFixed(2)} BB
                  </span>
                </div>
              );
            })}
          </div>

          {/* Combo EV grid */}
          {handData.combos && handData.combos.length > 0 && (
            <div className="border-t border-border pt-2">
              <ComboGrid
                combos={handData.combos}
                actionOptions={actionOptions}
              />
            </div>
          )}
        </div>
      )}

      {!selectedHand && (
        <div className="text-xs text-muted-foreground py-2">
          Click a hand in the grid to see details
        </div>
      )}

      {/* Legend */}
      <div className="space-y-1.5">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Legend
        </span>
        <div className="space-y-1">
          {actionOptions.map((opt) => {
            const summary = result.actions[opt.key];
            if (!summary) return null;
            return (
              <div key={opt.key} className="flex items-center gap-2 text-xs">
                <div
                  className={`w-3 h-3 rounded-sm ${opt.colour.split(" ")[0] ?? "bg-muted"}`}
                />
                <span className="text-muted-foreground">{opt.label}</span>
                <span className="text-foreground ml-auto">
                  {summary.bestActionCount} hands
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
