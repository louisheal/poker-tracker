import { getRanges } from "@/api";
import RangeGrid from "@/components/rangeGrid";
import { Button } from "@/components/ui/button";
import type { Ranges } from "@/models";
import { useEffect, useState } from "react";

type Positions = "LJ" | "HJ" | "CO" | "BTN" | "SB" | "BB";
type PotType = "SRP" | "THREE_BET" | "FOUR_BET";

const INIT_POS = "LJ";
const INIT_TYPE = "THREE_BET";

const POSITIONS: Record<PotType, { value: Positions; label: string }[]> = {
  SRP: [
    { value: "LJ", label: "LJ" },
    { value: "HJ", label: "HJ" },
    { value: "CO", label: "CO" },
    { value: "BTN", label: "BTN" },
    { value: "SB", label: "SB" },
  ],
  THREE_BET: [
    { value: "LJ", label: "v LJ" },
    { value: "HJ", label: "v HJ" },
    { value: "CO", label: "v CO" },
    { value: "BTN", label: "v BTN" },
    { value: "SB", label: "v SB" },
  ],
  FOUR_BET: [
    { value: "LJ", label: "LJ" },
    { value: "HJ", label: "HJ" },
    { value: "CO", label: "CO" },
    { value: "BTN", label: "BTN" },
    { value: "SB", label: "SB" },
    { value: "BB", label: "BB" },
  ],
};

interface PositionSelectorProps {
  positions: { value: Positions; label: string }[];
  selectedPosition: Positions;
  setSelectedRange: (position: Positions) => void;
}

const PositionSelector = ({
  positions,
  selectedPosition,
  setSelectedRange,
}: PositionSelectorProps) => (
  <div style={{ display: "flex", flexDirection: "row", alignItems: "center" }}>
    {positions.map(({ value, label }) => (
      <Button
        key={value}
        variant={selectedPosition === value ? "outline" : "default"}
        onClick={() => setSelectedRange(value)}
      >
        {label}
      </Button>
    ))}
  </div>
);

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
      <Button
        variant={props.selectedPot === "SRP" ? "outline" : "default"}
        onClick={props.setSrp}
      >
        SRP
      </Button>
      <Button
        variant={props.selectedPot === "THREE_BET" ? "outline" : "default"}
        onClick={props.setThreeBetPot}
      >
        3BET
      </Button>
      <Button
        variant={props.selectedPot === "FOUR_BET" ? "outline" : "default"}
        onClick={props.setFourBetPot}
      >
        4BET
      </Button>
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

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <PotSelector
        setSrp={setSrp}
        setThreeBetPot={setThreeBet}
        setFourBetPot={setFourBet}
        selectedPot={potType}
      />
      <PositionSelector
        positions={POSITIONS[potType]}
        selectedPosition={selectedRange}
        setSelectedRange={setSelectedRange}
      />
      <RangeGrid hands={ranges[potType][selectedRange]} />
    </div>
  );
};
