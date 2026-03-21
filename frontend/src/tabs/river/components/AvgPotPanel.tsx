import type { FlopActionLine, AvgPotStats } from "@/models";

const AVG_POT_LINES: { key: FlopActionLine; label: string }[] = [
  { key: "XX", label: "XX" },
  { key: "XBC", label: "XBC" },
  { key: "XBRC", label: "XBRC" },
  { key: "BC", label: "BC" },
];

interface Props {
  avgPot: { [key in FlopActionLine]: AvgPotStats } | undefined;
}

export const AvgPotPanel = ({ avgPot }: Props) => {
  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Avg Pot Size (BB)
        </h3>
      </div>
      <div className="grid grid-cols-2 gap-4">
        {AVG_POT_LINES.map(({ key, label }) => {
          const stats = avgPot?.[key];
          const value = stats?.avg_pot_bb ?? 0;
          return (
            <div key={key} className="flex flex-col items-center gap-2">
              <div className="w-25 h-25 rounded-full border-[7px] border-border flex items-center justify-center">
                <span className="text-lg font-bold text-foreground">
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
