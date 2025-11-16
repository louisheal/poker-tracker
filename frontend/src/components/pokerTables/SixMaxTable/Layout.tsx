interface Props {
  btnPos: number;
  children?: React.ReactNode[];
  correct: boolean | undefined;
}

const seatPositions = [
  { top: "50%", left: "95%", transform: "translate(-50%, -50%)" },
  { top: "78%", left: "66%", transform: "translate(-50%, -50%)" },
  { top: "78%", left: "34%", transform: "translate(-50%, -50%)" },
  { top: "50%", left: "5%", transform: "translate(-50%, -50%)" },
  { top: "22%", left: "34%", transform: "translate(-50%, -50%)" },
  { top: "22%", left: "66%", transform: "translate(-50%, -50%)" },
];

const btnPositions = [
  { top: "55%", left: "90%", transform: "translate(-50%, -50%)" },
  { top: "73%", left: "61%", transform: "translate(-50%, -50%)" },
  { top: "73%", left: "29%", transform: "translate(-50%, -50%)" },
  { top: "45%", left: "10%", transform: "translate(-50%, -50%)" },
  { top: "27%", left: "39%", transform: "translate(-50%, -50%)" },
  { top: "27%", left: "71%", transform: "translate(-50%, -50%)" },
];

const Layout = (props: Props) => {
  return (
    <div
      style={{
        height: "100%",
        width: "100%",
        justifyItems: "center",
        alignContent: "center",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          backgroundColor: props.correct ? "darkgreen" : "darkred",
          width: "90%",
          height: "60%",
          borderRadius: "43%",
          borderStyle: "solid",
        }}
      />
      {props.children?.map((child, index) => (
        <div
          key={index}
          style={{
            position: "absolute",
            ...seatPositions[index],
            width: "6%",
            aspectRatio: "1",
          }}
        >
          {child}
        </div>
      ))}
      <div
        style={{
          position: "absolute",
          ...btnPositions[props.btnPos],
          borderRadius: "100%",
          backgroundColor: "white",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          width: "3%",
          aspectRatio: "1",
        }}
      >
        <h1 style={{ margin: 0, fontSize: "100%", color: "black" }}>B</h1>
      </div>
    </div>
  );
};

export default Layout;
