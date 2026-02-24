import { getRanges } from "@/api";
import RangeGrid from "@/components/rangeGrid";
import { Button } from "@/components/ui/button";
import type { RangeResponse } from "@/models";
import { useEffect, useState } from "react";

type Positions = "LJ" | "HJ" | "CO" | "BTN" | "SB" | "BB";
const INIT_POS = "LJ";

export const Ranges = () => {
  const [ranges, setRanges] = useState<RangeResponse>();
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
      <Button onClick={() => setSelectedRange("BB")}>BB</Button>
      <RangeGrid hands={ranges[selectedRange].hands} />
    </>
  );
};
