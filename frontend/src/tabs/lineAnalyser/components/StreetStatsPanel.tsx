import { SpeedDial } from "@/components/SpeedDial";

interface Props {
  street: "flop" | "turn";
  stats: Record<string, number> & { hand_count: number };
  isPfr: boolean;
}

export const StreetStatsPanel = ({ street, stats, isPfr }: Props) => {
  if (street === "turn") {
    return (
      <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            {isPfr ? "PFR" : "DEF"} — Turn Stats
          </h3>
          <p className="text-xs text-muted-foreground">
            {stats.hand_count} hands
          </p>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <SpeedDial value={stats.hero_bet_pct ?? 0} label="Hero Bet" />
          <SpeedDial
            value={stats.villain_fold_to_hero_bet_pct ?? 0}
            label="Villain Fold"
          />
          <SpeedDial
            value={stats.villain_raise_to_hero_bet_pct ?? 0}
            label="Villain Raise"
          />
        </div>
        <div className="grid grid-cols-3 gap-4">
          <SpeedDial value={stats.villain_bet_pct ?? 0} label="Villain Bet" />
          <SpeedDial
            value={stats.hero_fold_to_villain_bet_pct ?? 0}
            label="Hero Fold"
          />
          <SpeedDial
            value={stats.hero_raise_to_villain_bet_pct ?? 0}
            label="Hero Raise"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          {isPfr ? "PFR" : "DEF"} — Flop Stats
        </h3>
        <p className="text-xs text-muted-foreground">
          {stats.hand_count} hands
        </p>
      </div>
      <div className="grid grid-cols-4 gap-4">
        <SpeedDial
          value={stats.cbet_pct ?? 0}
          label={isPfr ? "Hero C-Bet" : "Villain C-Bet"}
        />
        <SpeedDial value={stats.fold_to_cbet_pct ?? 0} label="Fold to C-Bet" />
        <SpeedDial
          value={stats.raise_to_cbet_pct ?? 0}
          label={isPfr ? "Villain Raise" : "Hero Raise"}
        />
        <SpeedDial
          value={stats.fold_to_cbet_raise_pct ?? 0}
          label={isPfr ? "Hero F2R" : "Villain F2R"}
        />
      </div>
      <div className="grid grid-cols-4 gap-4">
        <SpeedDial
          value={stats.donk_bet_pct ?? 0}
          label={isPfr ? "Villain Donk" : "Hero Donk"}
        />
        <SpeedDial value={stats.fold_to_donk_pct ?? 0} label="Fold to Donk" />
        <SpeedDial
          value={stats.raise_to_donk_pct ?? 0}
          label={isPfr ? "Hero Raise" : "Villain Raise"}
        />
        <SpeedDial
          value={stats.fold_to_donk_raise_pct ?? 0}
          label={isPfr ? "Villain F2R" : "Hero F2R"}
        />
      </div>
    </div>
  );
};
