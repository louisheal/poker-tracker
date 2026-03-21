import { SpeedDial } from "@/components/SpeedDial";

interface Props {
  stats: {
    hand_count: number;
    cbet_pct: number;
    fold_to_cbet_pct: number;
    raise_to_cbet_pct: number;
    fold_to_cbet_raise_pct: number;
    donk_bet_pct: number;
    fold_to_donk_pct: number;
    raise_to_donk_pct: number;
    fold_to_donk_raise_pct: number;
  };
  isPfr: boolean;
}

export const StreetStatsPanel = ({ stats, isPfr }: Props) => (
  <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-6">
    <div className="flex flex-col gap-1">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
        {isPfr ? "PFR" : "DEF"} — Flop Stats
      </h3>
      <p className="text-xs text-muted-foreground">
        {stats.hand_count} hands
      </p>
    </div>
    {/* C-bet row */}
    <div className="grid grid-cols-4 gap-4">
      <SpeedDial
        value={stats.cbet_pct}
        label={isPfr ? "Hero C-Bet" : "Villain C-Bet"}
      />
      <SpeedDial value={stats.fold_to_cbet_pct} label="Fold to C-Bet" />
      <SpeedDial
        value={stats.raise_to_cbet_pct}
        label={isPfr ? "Villain Raise" : "Hero Raise"}
      />
      <SpeedDial
        value={stats.fold_to_cbet_raise_pct}
        label={isPfr ? "Hero F2R" : "Villain F2R"}
      />
    </div>
    {/* Donk row */}
    <div className="grid grid-cols-4 gap-4">
      <SpeedDial
        value={stats.donk_bet_pct}
        label={isPfr ? "Villain Donk" : "Hero Donk"}
      />
      <SpeedDial value={stats.fold_to_donk_pct} label="Fold to Donk" />
      <SpeedDial
        value={stats.raise_to_donk_pct}
        label={isPfr ? "Hero Raise" : "Villain Raise"}
      />
      <SpeedDial
        value={stats.fold_to_donk_raise_pct}
        label={isPfr ? "Villain F2R" : "Hero F2R"}
      />
    </div>
  </div>
);
