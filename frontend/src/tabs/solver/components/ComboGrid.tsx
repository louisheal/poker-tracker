import type { SolverComboResult } from "@/models";
import type { ActionOption } from "../types";

interface Props {
  combos: SolverComboResult[];
  actionOptions: ActionOption[];
}

export const ComboGrid = ({ combos, actionOptions }: Props) => {
  if (combos.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
        Combos
      </span>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr>
              <th className="text-left font-medium text-muted-foreground pr-2 pb-1">
                Hand
              </th>
              {actionOptions.map((opt) => (
                <th
                  key={opt.key}
                  className="text-right font-medium text-muted-foreground px-1 pb-1 whitespace-nowrap"
                >
                  {opt.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {combos.map((combo) => (
              <tr key={combo.combo}>
                <td className="font-mono text-foreground pr-2 py-0.5">
                  {combo.combo}
                </td>
                {actionOptions.map((opt) => {
                  const ev = combo.evs[opt.key] ?? 0;
                  const isBest = opt.key === combo.bestAction;
                  return (
                    <td
                      key={opt.key}
                      className={`text-right tabular-nums px-1 py-0.5 rounded-sm ${
                        isBest
                          ? `${opt.colour} font-semibold`
                          : "text-muted-foreground"
                      }`}
                    >
                      {ev >= 0 ? "+" : ""}
                      {ev.toFixed(1)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
