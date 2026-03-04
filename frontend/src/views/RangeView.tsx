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
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
      }}
    >
      <Button onClick={() => props.setSelectedRange("LJ")}>LJ</Button>
      <Button onClick={() => props.setSelectedRange("HJ")}>HJ</Button>
      <Button onClick={() => props.setSelectedRange("CO")}>CO</Button>
      <Button onClick={() => props.setSelectedRange("BTN")}>BTN</Button>
      <Button onClick={() => props.setSelectedRange("SB")}>SB</Button>
    </div>
  );
};

interface ThreeBetSelectorProps {
  setSelectedRange: (position: Positions) => void;
}

const ThreeBetSelector = (props: ThreeBetSelectorProps) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
      }}
    >
      <Button onClick={() => props.setSelectedRange("LJ")}>v LJ</Button>
      <Button onClick={() => props.setSelectedRange("HJ")}>v HJ</Button>
      <Button onClick={() => props.setSelectedRange("CO")}>v CO</Button>
      <Button onClick={() => props.setSelectedRange("BTN")}>v BTN</Button>
      <Button onClick={() => props.setSelectedRange("SB")}>v SB</Button>
    </div>
  );
};

interface FourBetSelectorProps {
  setSelectedRange: (position: Positions) => void;
}

const FourBetSelector = (props: FourBetSelectorProps) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
      }}
    >
      <Button onClick={() => props.setSelectedRange("LJ")}>LJ</Button>
      <Button onClick={() => props.setSelectedRange("HJ")}>HJ</Button>
      <Button onClick={() => props.setSelectedRange("CO")}>CO</Button>
      <Button onClick={() => props.setSelectedRange("BTN")}>BTN</Button>
      <Button onClick={() => props.setSelectedRange("SB")}>SB</Button>
      <Button onClick={() => props.setSelectedRange("BB")}>BB</Button>
    </div>
  );
};

interface PotSelectorProps {
  setSrp: () => void;
  setThreeBetPot: () => void;
  setFourBetPot: () => void;
  selectedPot: PotType;
}

const PotSelector = (props: PotSelectorProps) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
      }}
    >
      <Button onClick={props.setSrp}>SRP</Button>
      <Button onClick={props.setThreeBetPot}>3BET</Button>
      <Button onClick={props.setFourBetPot}>4BET</Button>
    </div>
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

  if (potType == "SRP") {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <PotSelector
          setSrp={setSrp}
          setThreeBetPot={setThreeBet}
          setFourBetPot={setFourBet}
        />
        <RfiPositionSelector setSelectedRange={setSelectedRange} />
        <RangeGrid hands={ranges[potType][selectedRange]} />
      </div>
    );
  }

  if (potType == "THREE_BET") {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <PotSelector
          setSrp={setSrp}
          setThreeBetPot={setThreeBet}
          setFourBetPot={setFourBet}
        />
        <ThreeBetSelector setSelectedRange={setSelectedRange} />
        <RangeGrid hands={ranges[potType][selectedRange]} />
      </div>
    );
  }

  if (potType == "FOUR_BET") {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <PotSelector
          setSrp={setSrp}
          setThreeBetPot={setThreeBet}
          setFourBetPot={setFourBet}
        />
        <FourBetSelector setSelectedRange={setSelectedRange} />
        <RangeGrid hands={ranges[potType][selectedRange]} />
      </div>
    );
  }

  return <></>;
};
