import "./App.css";
import SixMaxTable from "./components/pokerTables/SixMaxTable";
import HandContainer from "./components/Hand";
import { useState } from "react";

function App() {
  const [btnPos, setBtnPos] = useState(0);

  const nextHand = () => {
    setBtnPos((prev) => (prev + 1) % 6);
  };

  return (
    <>
      <SixMaxTable btnPos={btnPos} />
      <HandContainer nextHand={nextHand} />
    </>
  );
}

export default App;
