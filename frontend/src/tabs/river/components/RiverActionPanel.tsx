import { SpeedDial } from "@/components/SpeedDial";
import type { RiverActionStats } from "@/models";

interface Props {
  stats: RiverActionStats | undefined;
}

export const RiverActionPanel = ({ stats }: Props) => {
  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          River Actions
        </h3>
        <p className="text-xs text-muted-foreground">
          {stats?.hand_count ?? 0} hands
        </p>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <SpeedDial value={stats?.hero_bet_pct ?? 0} label="Hero Bet" />
        <SpeedDial
          value={stats?.villain_fold_to_hero_bet_pct ?? 0}
          label="Villain Fold"
        />
        <SpeedDial
          value={stats?.villain_raise_to_hero_bet_pct ?? 0}
          label="Villain Raise"
        />
      </div>
      <div className="border-t border-border" />
      <div className="grid grid-cols-3 gap-4">
        <SpeedDial value={stats?.villain_bet_pct ?? 0} label="Villain Bet" />
        <SpeedDial
          value={stats?.hero_fold_to_villain_bet_pct ?? 0}
          label="Hero Fold"
        />
        <SpeedDial
          value={stats?.hero_raise_to_villain_bet_pct ?? 0}
          label="Hero Raise"
        />
      </div>
    </div>
  );
};
