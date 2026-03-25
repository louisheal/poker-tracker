import type { HandEvResponse, HandEvRow } from "@/models";

interface HandEvPanelProps {
  data: HandEvResponse | null;
}

interface DisplayRow {
  made: string;
  flush_draw: string;
  straight_draw: string;
  label: string;
}

const DISPLAY_ROWS: DisplayRow[] = [
  { made: "STRAIGHT_FLUSH", flush_draw: "NONE", straight_draw: "NONE", label: "Str Flush" },
  { made: "QUADS", flush_draw: "NONE", straight_draw: "NONE", label: "Quads" },
  { made: "FULL_HOUSE", flush_draw: "NONE", straight_draw: "NONE", label: "Full House" },
  { made: "FLUSH", flush_draw: "NONE", straight_draw: "NONE", label: "Flush" },
  { made: "STRAIGHT", flush_draw: "NONE", straight_draw: "NONE", label: "Straight" },
  { made: "SET", flush_draw: "NONE", straight_draw: "NONE", label: "Trips" },
  { made: "TWO_PAIR", flush_draw: "NONE", straight_draw: "NONE", label: "Two Pair" },
  { made: "OVERPAIR", flush_draw: "NONE", straight_draw: "NONE", label: "Overpair" },
  { made: "TOP_PAIR", flush_draw: "NONE", straight_draw: "NONE", label: "Top Pair" },
  { made: "PAIR", flush_draw: "NONE", straight_draw: "NONE", label: "Mid Pair" },
  { made: "ACE_HIGH", flush_draw: "NONE", straight_draw: "NONE", label: "A High" },
  { made: "NO_MADE_HAND", flush_draw: "FRONT_DOOR", straight_draw: "OESD", label: "FD + OESD" },
  { made: "NO_MADE_HAND", flush_draw: "FRONT_DOOR", straight_draw: "GUTSHOT", label: "FD + Gutshot" },
  { made: "NO_MADE_HAND", flush_draw: "FRONT_DOOR", straight_draw: "NONE", label: "Frontdoor Flush" },
  { made: "NO_MADE_HAND", flush_draw: "BACK_DOOR", straight_draw: "NONE", label: "Backdoor Flush" },
  { made: "NO_MADE_HAND", flush_draw: "NONE", straight_draw: "OESD", label: "OESD" },
  { made: "NO_MADE_HAND", flush_draw: "NONE", straight_draw: "GUTSHOT", label: "Gutshot" },
  { made: "NO_MADE_HAND", flush_draw: "NONE", straight_draw: "NONE", label: "No Made Hand" },
];

const ACTION_LABELS: Record<string, string> = {
  X: "Check",
  F: "Fold",
  C: "Call",
  R: "Raise",
};

function actionLabel(action: string): string {
  if (ACTION_LABELS[action]) return ACTION_LABELS[action];
  if (action.startsWith("B")) return `B${action.slice(1)}%`;
  return action;
}

function matchRow(row: HandEvRow, display: DisplayRow): boolean {
  return (
    row.made === display.made &&
    row.flush_draw === display.flush_draw &&
    row.straight_draw === display.straight_draw
  );
}

function filterRows(rows: HandEvRow[]): Array<{ row: HandEvRow; label: string }> {
  const result: Array<{ row: HandEvRow; label: string }> = [];
  for (const display of DISPLAY_ROWS) {
    const match = rows.find((r) => matchRow(r, display));
    if (match) {
      result.push({ row: match, label: display.label });
    }
  }
  return result;
}

function evColor(ev: number): string {
  if (ev > 0) return "text-emerald-400";
  if (ev < 0) return "text-red-400";
  return "text-muted-foreground";
}

export const HandEvPanel = ({ data }: HandEvPanelProps) => {
  if (!data || data.hand_count === 0 || data.next_actor !== "hero") {
    return (
      <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-4 row-span-2">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Hand Class EV
        </h3>
        <p className="text-sm text-muted-foreground">
          {data?.next_actor === "villain" ? "Villain's decision node" : "No data available"}
        </p>
      </div>
    );
  }

  const displayRows = filterRows(data.rows);
  const actions = data.available_actions;
  const villain = data.villain_data;

  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-3 row-span-2 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Hand Class EV
        </h3>
        <span className="text-xs text-muted-foreground">
          {data.hand_count} hands
        </span>
      </div>

      {/* Villain summary */}
      <div className="text-xs text-muted-foreground flex gap-3">
        <span>
          Villain: {villain.fold_pct}% fold · {villain.call_pct}% call ·{" "}
          {villain.raise_pct}% raise
        </span>
        <span>Pot: {data.pot_bb.toFixed(1)} BB</span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-muted-foreground">
              <th className="text-left py-1.5 pr-3 font-medium">Hand Class</th>
              {actions.map((a) => (
                <th key={a} className="text-right py-1.5 px-2 font-medium">
                  {actionLabel(a)}
                </th>
              ))}
              <th className="text-right py-1.5 pl-2 font-medium">Best</th>
            </tr>
          </thead>
          <tbody>
            {displayRows.map(({ row, label }, i) => {
              const bestEv = Math.max(...Object.values(row.evs));
              return (
                <tr
                  key={i}
                  className="border-b border-border/50 last:border-b-0"
                >
                  <td className="py-1.5 pr-3 font-medium text-foreground whitespace-nowrap">
                    {label}
                  </td>
                  {actions.map((a) => {
                    const ev = row.evs[a];
                    const isBest = ev === bestEv;
                    return (
                      <td
                        key={a}
                        className={`text-right py-1.5 px-2 tabular-nums ${evColor(ev)} ${isBest ? "font-bold" : ""}`}
                      >
                        {isBest ? "★ " : ""}
                        {ev.toFixed(1)}
                      </td>
                    );
                  })}
                  <td className="text-right py-1.5 pl-2 text-muted-foreground whitespace-nowrap">
                    {actionLabel(row.best_action)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
