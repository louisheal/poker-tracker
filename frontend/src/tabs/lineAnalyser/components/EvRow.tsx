interface Props {
  label: string;
  evBb: number;
  count: number;
  onClick?: () => void;
  indented?: boolean;
  expandable?: boolean;
  expanded?: boolean;
  onToggleExpand?: () => void;
}

export const EvRow = ({ label, evBb, count, onClick, indented, expandable, expanded, onToggleExpand }: Props) => {
  const color =
    evBb > 0
      ? "text-emerald-400"
      : evBb < 0
        ? "text-red-400"
        : "text-muted-foreground";
  return (
    <div
      className={`flex items-center justify-between py-2 ${indented ? "ml-4" : ""} ${onClick ? "cursor-pointer hover:bg-muted/50 rounded px-2 -mx-2 transition-colors" : ""}`}
      onClick={onClick}
    >
      <div className="flex items-baseline gap-2">
        <span className={indented ? "text-xs" : "text-sm"}>{label}</span>
        <span className="text-xs text-muted-foreground">{count} hands</span>
        {expandable && (
          <span
            role="button"
            className="text-xs text-muted-foreground hover:text-foreground cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand?.();
            }}
          >
            {expanded ? "▾" : "▸"}
          </span>
        )}
      </div>
      <span className={`${indented ? "text-xs" : "text-sm"} font-semibold tabular-nums ${color}`}>
        {evBb > 0 ? "+" : ""}
        {evBb.toFixed(1)} BB
      </span>
    </div>
  );
};
