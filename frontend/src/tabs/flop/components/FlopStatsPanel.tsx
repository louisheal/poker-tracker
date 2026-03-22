import { SpeedDial } from "@/components/SpeedDial";
import type { CbetStats } from "@/models";

interface Props {
  title: string;
  role: "PFR" | "DEF";
  stats: CbetStats | undefined;
}

export const FlopStatsPanel = ({ title, role, stats }: Props) => {
  const isPfr = role === "PFR";
  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          {title}
        </h3>
        <p className="text-xs text-muted-foreground">
          {stats?.hand_count ?? 0} hands
        </p>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <SpeedDial
          value={stats?.cbet_pct ?? 0}
          label={isPfr ? "Hero C-Bet" : "Villain C-Bet"}
        />
        <SpeedDial value={stats?.fcbet_pct ?? 0} label="Fold to C-Bet" />
        <SpeedDial
          value={stats?.raise_to_cbet_pct ?? 0}
          label={isPfr ? "Villain Raise" : "Hero Raise"}
        />
        <SpeedDial
          value={stats?.donk_bet_pct ?? 0}
          label={isPfr ? "Villain Donk Bet" : "Hero Donk Bet"}
        />
        <SpeedDial
          value={stats?.fold_to_donk_pct ?? 0}
          label="Fold to Donk Bet"
        />
        <SpeedDial
          value={stats?.raise_to_donk_pct ?? 0}
          label={isPfr ? "Hero Raise" : "Villain Raise"}
        />
      </div>
    </div>
  );
};
