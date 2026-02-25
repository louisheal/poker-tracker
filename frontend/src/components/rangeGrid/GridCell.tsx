interface Props {
  handKey: string;
  folds: number;
  raises: number;
}

const green = "rgb(34, 197, 94)";
const red = "rgb(239, 68, 68)";

export const GridCell = (props: Props) => {
  const total = props.folds + props.raises;
  const raisePercent = total === 0 ? 0 : (props.raises / total) * 100;

  const backgroundStyle = {
    background: `linear-gradient(to right, ${green} 0%, ${green} ${raisePercent}%, ${red} ${raisePercent}%, ${red} 100%)`,
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
