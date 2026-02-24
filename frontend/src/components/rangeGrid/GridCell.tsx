interface Props {
  handKey: string;
  folds: number;
  raises: number;
}

export const GridCell = (props: Props) => {
  const total = props.folds + props.raises;
  const foldPercent = total === 0 ? 0 : (props.folds / total) * 100;

  const backgroundStyle = {
    background: `linear-gradient(to right, rgb(239, 68, 68) 0%, rgb(239, 68, 68) ${foldPercent}%, rgb(34, 197, 94) ${foldPercent}%, rgb(34, 197, 94) 100%)`,
  };

  // if (props.raises === 0) {
  //   backgroundStyle = {
  //     background: "rgb(0, 0, 0)",
  //   };
  // }

  return (
    <div
      style={total === 0 ? {} : backgroundStyle}
      className="w-[calc(94%/13)] aspect-square flex items-center justify-center border"
    >
      <div>
        <p>{props.handKey}</p>
        {/* <p>{props.folds}</p>
        <p>{props.raises}</p> */}
      </div>
    </div>
  );
};
