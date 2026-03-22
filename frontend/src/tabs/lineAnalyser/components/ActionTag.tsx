interface Props {
  label: string;
  isActive: boolean;
  isFuture: boolean;
  onClick: () => void;
  onRemove?: () => void;
  showArrow?: boolean;
}

export const ActionTag = ({
  label,
  isActive,
  isFuture,
  onClick,
  onRemove,
  showArrow = true,
}: Props) => (
  <div className="flex items-center gap-1">
    {showArrow && (
      <span
        className={`text-xs ${isFuture ? "text-muted-foreground/40" : "text-muted-foreground"}`}
      >
        →
      </span>
    )}
    <button
      onClick={onClick}
      className={`
        inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-colors
        ${
          isActive
            ? "bg-primary text-primary-foreground"
            : isFuture
              ? "bg-muted/40 text-muted-foreground/50 hover:bg-muted/60"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
        }
      `}
    >
      {label}
      {onRemove && (
        <span
          role="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ml-1 hover:text-destructive cursor-pointer"
        >
          ×
        </span>
      )}
    </button>
  </div>
);
