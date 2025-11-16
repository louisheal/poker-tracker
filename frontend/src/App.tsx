import "./App.css";
import SixMaxTable from "./components/pokerTables/SixMaxTable";
import HandContainer from "./components/Hand";
import { useState } from "react";
import RangeContainer from "./components/ranges/RangeContainer";
import { Box, Dialog } from "@mui/material";

function App() {
  const [btnPos, setBtnPos] = useState(1);
  const [isOpen, setIsOpen] = useState(false);
  const [correct, setCorrect] = useState<boolean | undefined>(undefined);

  const nextHand = (correct: boolean) => {
    let nextPos = (btnPos + 1) % 6;
    if (nextPos === 0) {
      nextPos = 1;
    }
    setBtnPos(nextPos);
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
        <RangeContainer />
      </Dialog>
    </>
  );
}

export default App;
