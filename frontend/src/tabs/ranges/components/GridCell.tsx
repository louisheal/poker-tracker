import "./rangeGrid.css";

interface Props {
  handKey: string;
  folds: number;
  raises: number;
  calls: number;
}

export const GridCell = (props: Props) => {
  const total = props.folds + props.raises + props.calls;
  const raisePercent = total === 0 ? 0 : (props.raises / total) * 100;
  const callPercent = total === 0 ? 0 : (props.calls / total) * 100;

  const ariaLabel = `${props.handKey}: ${props.raises} raises, ${props.calls} calls, ${props.folds} folds`;

  const isEmpty = total === 0;

  const style: Record<string, string> = isEmpty
    ? {}
    : ({
        ["--rg-raise-percent"]: `${raisePercent}%`,
        ["--rg-call-percent"]: `${callPercent}%`,
      } as Record<string, string>);

  return (
    <div
      role="button"
      tabIndex={0}
      title={ariaLabel}
      aria-label={ariaLabel}
      style={style}
      className={`rg-cell box-border aspect-square flex items-center justify-center rounded-sm ${isEmpty ? "rg-empty" : ""}`}
    >
      <p className="text-xs select-none">{props.handKey}</p>
    </div>
  );
};

export default GridCell;
