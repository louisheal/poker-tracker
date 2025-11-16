import "./App.css";
import SixMaxTable from "./components/pokerTables/SixMaxTable";
import HandContainer from "./components/Hand";
import { useState } from "react";
import RangeContainer from "./components/ranges/RangeContainer";
import { Dialog, DialogTitle } from "@mui/material";

function App() {
  const [btnPos, setBtnPos] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  const nextHand = () => {
    setBtnPos((prev) => (prev + 1) % 6);
  };

  return (
    <>
      <button
        style={{ position: "relative", zIndex: 1 }}
        onClick={() => setIsOpen(true)}
      >
        Show Range
      </button>
      <SixMaxTable btnPos={btnPos} />
      <HandContainer nextHand={nextHand} pos={btnPos} />
      <Dialog
        open={isOpen}
        onClose={() => setIsOpen(false)}
        maxWidth={false}
        slotProps={{
          paper: {
            sx: { backgroundColor: "#242424", color: "white" },
          },
        }}
      >
        <DialogTitle>Player Ranges</DialogTitle>
        <RangeContainer pos={btnPos} />
      </Dialog>
    </>
  );
}

export default App;
