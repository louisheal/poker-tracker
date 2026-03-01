import { getRanges } from "@/api";
import RangeGrid from "@/components/rangeGrid";
import { Button } from "@/components/ui/button";
import type { Ranges } from "@/models";
import { useEffect, useState } from "react";

type Positions = "LJ" | "HJ" | "CO" | "BTN" | "SB" | "BB";
type PotType = "SRP" | "THREE_BET" | "FOUR_BET";

const INIT_POS = "LJ";
const INIT_TYPE = "THREE_BET";

interface RfiSelectorProps {
  setSelectedRange: (position: Positions) => void;
}

const RfiPositionSelector = (props: RfiSelectorProps) => {
  return (
    <>
      <Button onClick={() => props.setSelectedRange("LJ")}>LJ</Button>
      <Button onClick={() => props.setSelectedRange("HJ")}>HJ</Button>
      <Button onClick={() => props.setSelectedRange("CO")}>CO</Button>
      <Button onClick={() => props.setSelectedRange("BTN")}>BTN</Button>
      <Button onClick={() => props.setSelectedRange("SB")}>SB</Button>
    </>
  );
};

interface ThreeBetSelectorProps {
  setSelectedRange: (position: Positions) => void;
}

const ThreeBetSelector = (props: ThreeBetSelectorProps) => {
  return (
    <>
      <Button onClick={() => props.setSelectedRange("LJ")}>v LJ</Button>
      <Button onClick={() => props.setSelectedRange("HJ")}>v HJ</Button>
      <Button onClick={() => props.setSelectedRange("CO")}>v CO</Button>
      <Button onClick={() => props.setSelectedRange("BTN")}>v BTN</Button>
      <Button onClick={() => props.setSelectedRange("SB")}>v SB</Button>
    </>
  );
};

interface FourBetSelectorProps {
  setSelectedRange: (position: Positions) => void;
}

const FourBetSelector = (props: FourBetSelectorProps) => {
  return (
    <>
      <Button onClick={() => props.setSelectedRange("LJ")}>LJ</Button>
      <Button onClick={() => props.setSelectedRange("HJ")}>HJ</Button>
      <Button onClick={() => props.setSelectedRange("CO")}>CO</Button>
      <Button onClick={() => props.setSelectedRange("BTN")}>BTN</Button>
      <Button onClick={() => props.setSelectedRange("SB")}>SB</Button>
      <Button onClick={() => props.setSelectedRange("BB")}>BB</Button>
    </>
  );
};

export const RangeView = () => {
  const [ranges, setRanges] = useState<Ranges>();
  const [selectedRange, setSelectedRange] = useState<Positions>(INIT_POS);
  const [potType, setPotType] = useState<PotType>(INIT_TYPE);

  useEffect(() => {
    const loadRanges = async () => {
      const ranges = await getRanges();
      setRanges(ranges);
    };

    loadRanges();
  }, []);

  if (ranges === undefined) {
    return;
  }

  const setSrp = () => {
    setSelectedRange("LJ");
    setPotType("SRP");
  };

  const setThreeBet = () => {
    setSelectedRange("LJ");
    setPotType("THREE_BET");
  };

  const setFourBet = () => {
    setSelectedRange("LJ");
    setPotType("FOUR_BET");
  };

  const PotSelector = () => {
    return (
      <>
        <Button onClick={setSrp}>SRP</Button>
        <Button onClick={setThreeBet}>3BET</Button>
        <Button onClick={setFourBet}>4BET</Button>
      </>
    );
  };

  if (potType == "SRP") {
    return (
      <>
        <PotSelector />
        <RfiPositionSelector setSelectedRange={setSelectedRange} />
        <RangeGrid hands={ranges[potType][selectedRange]} />
      </>
    );
  }

  console.log(ranges);

  if (potType == "THREE_BET") {
    return (
      <>
        <PotSelector />
        <ThreeBetSelector setSelectedRange={setSelectedRange} />
        <RangeGrid hands={ranges[potType][selectedRange]} />
      </>
    );
  }

  if (potType == "FOUR_BET") {
    return (
      <>
        <PotSelector />
        <FourBetSelector setSelectedRange={setSelectedRange} />
        <RangeGrid hands={ranges[potType][selectedRange]} />
      </>
    );
  }

  return <></>;
};
