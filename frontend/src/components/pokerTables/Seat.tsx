interface Props {
  label: string;
}

const Seat = (props: Props) => {
  return (
    <div
      style={{
        borderRadius: "100%",
        backgroundColor: "black",
        borderColor: "white",
        borderStyle: "solid",
        display: "flex",
        width: "100%",
        height: "100%",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {props.label}
    </div>
  );
};

export default Seat;
