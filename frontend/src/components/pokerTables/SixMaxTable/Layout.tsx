interface Props {
  children?: React.ReactNode[];
}

const seatPositions = [
  { top: "22%", left: "34%", transform: "translate(-50%, -50%)" },
  { top: "22%", left: "66%", transform: "translate(-50%, -50%)" },
  { top: "50%", left: "94%", transform: "translate(-50%, -50%)" },
  { top: "78%", left: "66%", transform: "translate(-50%, -50%)" },
  { top: "78%", left: "34%", transform: "translate(-50%, -50%)" },
  { top: "50%", left: "6%", transform: "translate(-50%, -50%)" },
];

const Layout = ({ children }: Props) => {
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
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          backgroundColor: "darkgreen",
          width: "90%",
          height: "60%",
          borderRadius: "50%",
          borderStyle: "solid",
        }}
      >
        <h1 style={{ paddingBottom: "2%" }}>Preflop Trainer</h1>
      </div>
      {children?.map((child, index) => (
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
    </div>
  );
};

export default Layout;
