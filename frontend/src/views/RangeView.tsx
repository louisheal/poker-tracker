import { getRanges } from "@/api";
import RangeGrid from "@/components/rangeGrid";
import { Button } from "@/components/ui/button";
import type { RfiRanges } from "@/models";
import { useEffect, useState } from "react";

type Positions = "LJ" | "HJ" | "CO" | "BTN" | "SB" | "BB";
const INIT_POS = "LJ";

export const RangeView = () => {
  const [ranges, setRanges] = useState<RfiRanges>();
  const [selectedRange, setSelectedRange] = useState<Positions>(INIT_POS);

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

  return (
    <>
      <Button onClick={() => setSelectedRange("LJ")}>LJ</Button>
      <Button onClick={() => setSelectedRange("HJ")}>HJ</Button>
      <Button onClick={() => setSelectedRange("CO")}>CO</Button>
      <Button onClick={() => setSelectedRange("BTN")}>BTN</Button>
      <Button onClick={() => setSelectedRange("SB")}>SB</Button>
      <RangeGrid hands={ranges[selectedRange]} />
    </>
  );
};
