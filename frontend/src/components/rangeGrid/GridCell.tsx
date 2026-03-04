interface Props {
  handKey: string;
  folds: number;
  raises: number;
  calls: number;
}

const blue = "rgb(60, 120, 250)";
const green = "rgb(34, 197, 94)";
const red = "rgb(239, 68, 68)";

export const GridCell = (props: Props) => {
  const total = props.folds + props.raises + props.calls;
  const raisePercent = total === 0 ? 0 : (props.raises / total) * 100;
  const callPercent = total === 0 ? 0 : (props.calls / total) * 100;

  const raises = `${red} 0%, ${red} ${raisePercent}%`;
  const calls = `${green} ${raisePercent}%, ${green} ${raisePercent + callPercent}%`;
  const folds = `${blue} ${raisePercent + callPercent}%, ${blue} 100%`;

  const backgroundStyle = {
    background: `linear-gradient(to right, ${raises}, ${calls}, ${folds})`,
    boxShadow: "inset 0 0 0 1px rgba(0,0,0,0.2)",
  };

  return (
    <div
      style={total === 0 ? {} : backgroundStyle}
      className="w-[calc(100%/13)] aspect-square flex items-center justify-center"
    >
      <p>{props.handKey}</p>
    </div>
  );
};
