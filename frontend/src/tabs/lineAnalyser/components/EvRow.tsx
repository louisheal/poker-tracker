interface Props {
  label: string;
  evBb: number;
  count: number;
  onClick?: () => void;
}

export const EvRow = ({ label, evBb, count, onClick }: Props) => {
  const color =
    evBb > 0
      ? "text-emerald-400"
      : evBb < 0
        ? "text-red-400"
        : "text-muted-foreground";
  return (
    <div
      className={`flex items-center justify-between py-2 ${onClick ? "cursor-pointer hover:bg-muted/50 rounded px-2 -mx-2 transition-colors" : ""}`}
      onClick={onClick}
    >
      <div className="flex items-baseline gap-2">
        <span className="text-sm">{label}</span>
        <span className="text-xs text-muted-foreground">{count} hands</span>
      </div>
      <span className={`text-sm font-semibold tabular-nums ${color}`}>
        {evBb > 0 ? "+" : ""}
        {evBb.toFixed(1)} BB
      </span>
    </div>
  );
};
