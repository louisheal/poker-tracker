import type { HandData } from "../../domain";

interface Props {
  range: HandData[][];
}

interface BoxProps {
  data: HandData;
}

const Box = (props: BoxProps) => {
  const { folds, raises } = props.data;
  const total = folds + raises;
  let gradient = "linear-gradient(to bottom, green 0%, green 100%)";
  if (total > 0) {
    const foldPercent = Math.round((folds / total) * 100);
    const raisePercent = 100 - foldPercent;
    gradient = `linear-gradient(to bottom, green 0%, green ${raisePercent}%, red ${
      raisePercent + 1
    }%, red 100%)`;
  } else {
    gradient = "linear-gradient(to bottom, red 0%, red 100%)";
  }
  return (
    <div
      style={{
        background: gradient,
        alignItems: "center",
        justifyItems: "center",
        width: "36px",
        aspectRatio: "1",
        display: "flex",
        justifyContent: "center",
        border: "1px solid #333",
      }}
    >
      <p style={{ margin: 0 }}>{props.data.key}</p>
    </div>
  );
};

const RangeDisplay = (props: Props) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
      }}
    >
      {props.range.map((row, index) => {
        return (
          <div
            key={index}
            style={{
              display: "flex",
              flex: "row",
            }}
          >
            {row.map((data, index) => {
              return <Box key={index} data={data}></Box>;
            })}
          </div>
        );
      })}
    </div>
  );
};

export default RangeDisplay;
