import type { FlopActionLine, ShowdownStats } from "@/models";

const SHOWDOWN_LINES: { key: FlopActionLine; label: string }[] = [
  { key: "XX", label: "XX" },
  { key: "XBC", label: "XBC" },
  { key: "XBRC", label: "XBRC" },
  { key: "BC", label: "BC" },
];

interface Props {
  showdown: { [key in FlopActionLine]: ShowdownStats } | undefined;
}

export const ShowdownPanel = ({ showdown }: Props) => {
  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Showdown Results (BB/hand)
        </h3>
      </div>
      <div className="grid grid-cols-2 gap-4">
        {SHOWDOWN_LINES.map(({ key, label }) => {
          const stats = showdown?.[key];
          const value = stats?.bb_per_hand ?? 0;
          const isPositive = value > 0;
          const isNegative = value < 0;
          return (
            <div key={key} className="flex flex-col items-center gap-2">
              <div className="w-25 h-25 rounded-full border-[7px] border-border flex items-center justify-center">
                <span
                  className={`text-lg font-bold ${isPositive ? "text-green-500" : isNegative ? "text-red-500" : "text-foreground"}`}
                >
                  {value >= 0 ? "+" : ""}
                  {value.toFixed(1)}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">{label}</span>
              <span className="text-xs text-muted-foreground">
                {stats?.hand_count ?? 0} hands
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
