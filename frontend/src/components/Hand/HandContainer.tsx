import { useEffect, useState } from "react";
import HandDisplay from "./Hand";
import type { HandDto } from "../../domain";
import { fetchHand } from "../../api";

const HandContainer = () => {
  const [hand, setHand] = useState<HandDto | undefined>(undefined);

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

  return <HandDisplay hand={hand} />;
};

export default HandContainer;
