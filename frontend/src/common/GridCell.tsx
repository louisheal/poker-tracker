import "./gridCell.css";

interface Props {
  handKey: string;

  /** Range mode: gradient from raise/call/fold counts */
  folds?: number;
  raises?: number;
  calls?: number;

  /** Solver mode: solid background colour (Tailwind classes) */
  colour?: string;

  onClick?: () => void;
  isSelected?: boolean;
  title?: string;
}

export const GridCell = ({
  handKey,
  folds = 0,
  raises = 0,
  calls = 0,
  colour,
  onClick,
  isSelected = false,
  title,
}: Props) => {
  const total = folds + raises + calls;
  const useSolid = colour !== undefined;

  const raisePercent = total === 0 ? 0 : (raises / total) * 100;
  const callPercent = total === 0 ? 0 : (calls / total) * 100;

  const ariaLabel =
    title ??
    (useSolid
      ? handKey
      : `${handKey}: ${raises} raises, ${calls} calls, ${folds} folds`);

  const isEmpty = !useSolid && total === 0;

  const gradientStyle: Record<string, string> =
    isEmpty || useSolid
      ? {}
      : {
          "--gc-raise-percent": `${raisePercent}%`,
          "--gc-call-percent": `${callPercent}%`,
        };

  const baseClass =
    "box-border aspect-square flex items-center justify-center rounded-sm";

  if (useSolid) {
    return (
      <button
        onClick={onClick}
        title={ariaLabel}
        aria-label={ariaLabel}
        className={`${baseClass} transition-all hover:brightness-125 ${colour} ${isSelected ? "ring-2 ring-white/80" : ""}`}
      >
        <span className="text-xs select-none">{handKey}</span>
      </button>
    );
  }

  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      role="button"
      tabIndex={0}
      title={ariaLabel}
      aria-label={ariaLabel}
      style={gradientStyle as React.CSSProperties}
      className={`grid-cell ${baseClass} ${isEmpty ? "grid-cell--empty" : ""} ${onClick ? "cursor-pointer hover:brightness-110" : ""} ${isSelected ? "ring-2 ring-white/80" : ""}`}
      onClick={onClick}
    >
      <span className="text-xs select-none">{handKey}</span>
    </Tag>
  );
};
