import { useEffect, useState } from "react";
import HandDisplay from "./HandDisplay";
import type { HandDto } from "../../domain";
import { fetchHand, foldHand, raiseHand } from "../../api";

interface Props {
  nextHand: (correct: boolean) => void;
  pos: number;
}

const HandContainer = (props: Props) => {
  const [hand, setHand] = useState<HandDto | undefined>(undefined);

  const getHand = async () => {
    const hand = await fetchHand();
    setHand(hand);
  };

  useEffect(() => {
    getHand();
  }, []);

  if (hand === undefined) {
    return;
  }

  const raise = async () => {
    const result = await raiseHand(hand.Id, props.pos);
    props.nextHand(result);
    await getHand();
  };

  const fold = async () => {
    const result = await foldHand(hand.Id, props.pos);
    props.nextHand(result);
    await getHand();
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        position: "relative",
      }}
    >
      <HandDisplay hand={hand} />
      <div style={{ display: "flex", gap: "6px", marginTop: "6px" }}>
        <button onClick={raise}>Raise</button>
        <button onClick={fold}>Fold</button>
      </div>
    </div>
  );
};

export default HandContainer;
