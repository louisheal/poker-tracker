import { useEffect, useState } from "react";
import HandDisplay from "./Hand";
import type { HandDto } from "../../domain";
import { fetchHand, foldHand, raiseHand } from "../../api";

const HandContainer = () => {
  const [hand, setHand] = useState<HandDto | undefined>(undefined);

  const raise = async () => {
    const hand = await raiseHand();
    setHand(hand);
  };

  const fold = async () => {
    const hand = await foldHand();
    setHand(hand);
  };

  useEffect(() => {
    const loadHand = async () => {
      const hand = await fetchHand();
      setHand(hand);
    };

    loadHand();
  }, []);

  if (hand === undefined) {
    return;
  }

  return (
    <>
      <HandDisplay hand={hand} />
      <div style={{ display: "flex" }}>
        <button onClick={raise}>Raise</button>
        <button onClick={fold}>Fold</button>
      </div>
    </>
  );
};

export default HandContainer;
