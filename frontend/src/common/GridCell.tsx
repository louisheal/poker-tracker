import "./gridCell.css";

interface GradientStop {
  color: string;
  percent: number;
}

interface Props {
  handKey: string;

  /** Range mode: gradient from raise/call/fold counts */
  folds?: number;
  raises?: number;
  calls?: number;

  /** Solver mode: solid background colour (Tailwind classes) */
  colour?: string;

  /** Solver mode: dynamic N-stop gradient for combo-level action distribution */
  gradientStops?: GradientStop[];

  /** Background opacity (0-1) for dimming cells. Text stays fully visible. */
  bgOpacity?: number;

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
  gradientStops,
  bgOpacity,
  onClick,
  isSelected = false,
  title,
}: Props) => {
  const total = folds + raises + calls;
  const useSolid = colour !== undefined && !gradientStops;
  const useGradientStops = gradientStops !== undefined && gradientStops.length > 0;

  const raisePercent = total === 0 ? 0 : (raises / total) * 100;
  const callPercent = total === 0 ? 0 : (calls / total) * 100;

  const ariaLabel =
    title ??
    (useSolid || useGradientStops
      ? handKey
      : `${handKey}: ${raises} raises, ${calls} calls, ${folds} folds`);

  const isEmpty = !useSolid && !useGradientStops && total === 0;

  // Build inline gradient for solver action distribution
  if (useGradientStops) {
    const stops: string[] = [];
    let cumulative = 0;
    for (const { color, percent } of gradientStops) {
      stops.push(`${color} ${cumulative}%`);
      cumulative += percent;
      stops.push(`${color} ${cumulative}%`);
    }
    const bg = stops.length > 0
      ? `linear-gradient(to right, ${stops.join(", ")})`
      : undefined;

    return (
      <button
        onClick={onClick}
        title={ariaLabel}
        aria-label={ariaLabel}
        style={{ background: bg }}
        className={`box-border aspect-square flex items-center justify-center rounded-sm transition-all hover:brightness-125 ${isSelected ? "ring-2 ring-white/80" : ""}`}
      >
        <span className="text-xs select-none text-white">{handKey}</span>
      </button>
    );
  }

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
    // When bgOpacity is set, render background as a separate layer so text stays fully visible
    if (bgOpacity !== undefined) {
      const alpha = Math.max(bgOpacity, 0.2);
      return (
        <button
          onClick={onClick}
          title={ariaLabel}
          aria-label={ariaLabel}
          className={`${baseClass} relative transition-all hover:brightness-125 ${isSelected ? "ring-2 ring-white/80" : ""}`}
        >
          <span
            className={`absolute inset-0 rounded-sm ${colour}`}
            style={{ opacity: alpha }}
            aria-hidden
          />
          <span className="relative text-xs select-none text-white">{handKey}</span>
        </button>
      );
    }
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
