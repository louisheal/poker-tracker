import type { ActionOption } from "../types";

interface Props {
  label: string;
  sublabel?: string;
  options: ActionOption[];
  selected: string | null;
  isViewed: boolean;
  onSelect: (action: string) => void;
  onNavigate: () => void;
}

export const DecisionTile = ({
  label,
  sublabel,
  options,
  selected,
  isViewed,
  onSelect,
  onNavigate,
}: Props) => (
  <div
    onClick={onNavigate}
    className={`flex flex-col gap-1 rounded-lg border p-2 min-w-[80px] shrink-0 cursor-pointer transition-colors ${
      isViewed
        ? "border-primary/60 bg-card ring-1 ring-primary/30"
        : "border-border bg-card/60 hover:border-border/80"
    }`}
  >
    <div className="text-center leading-tight">
      <div className="text-[11px] font-semibold text-foreground">{label}</div>
      {sublabel && (
        <div className="text-[9px] text-muted-foreground">{sublabel}</div>
      )}
    </div>
    <div className="flex flex-col gap-0.5">
      {options.map((opt) => {
        const isSelected = opt.key === selected;
        return (
          <button
            key={opt.key}
            onClick={(e) => {
              e.stopPropagation();
              onSelect(opt.key);
            }}
            className={`px-2 py-1 rounded text-[11px] font-medium transition-colors whitespace-nowrap ${
              isSelected
                ? `${opt.colour} ring-1 ring-white/20`
                : "bg-muted/40 text-muted-foreground hover:bg-muted/70"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  </div>
);
