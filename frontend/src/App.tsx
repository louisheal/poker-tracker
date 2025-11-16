import "./App.css";
import SixMaxTable from "./components/pokerTables/SixMaxTable";
import HandContainer from "./components/Hand";
import { useState } from "react";
import RangeContainer from "./components/ranges/RangeContainer";
import { Box, Dialog, DialogTitle } from "@mui/material";

function App() {
  const [btnPos, setBtnPos] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [correct, setCorrect] = useState<boolean | undefined>(undefined);

  const nextHand = (correct: boolean) => {
    setBtnPos((prev) => (prev + 1) % 6);
    setCorrect(correct);
  };

  return (
    <>
      <Box gap="6px" display="flex" flexDirection="column" alignItems="center">
        <SixMaxTable correct={correct} btnPos={btnPos} />
        <HandContainer
          nextHand={(correct: boolean) => nextHand(correct)}
          pos={btnPos}
        />
        <button
          style={{ position: "relative", zIndex: 1 }}
          onClick={() => setIsOpen(true)}
        >
          Show Ranges
        </button>
      </Box>
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
        <RangeContainer />
      </Dialog>
    </>
  );
}

export default App;
