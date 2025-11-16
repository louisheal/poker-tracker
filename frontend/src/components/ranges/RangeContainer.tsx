import { useEffect, useState } from "react";
import { fetchRange } from "../../api";
import RangeDisplay from "./RangeDisplay";
import type { Ranges } from "../../domain";
import { Box } from "@mui/material";

const rangeNames = ["Small Blind", "Button", "Cutoff", "Hijack", "Lojack"];

const RangeContainer = () => {
  const [ranges, setRanges] = useState<Record<number, Ranges> | undefined>();

  useEffect(() => {
    const getRanges = async () => {
      for (let i = 1; i < 6; i++) {
        const data = await fetchRange(i);
        setRanges((prev) => ({ ...prev, [i]: data }));
      }
    };

    getRanges();
  }, []);

  if (ranges === undefined) {
    return <></>;
  }

  return (
    <Box display="flex" flexDirection="column" margin="16px" gap="16px">
      {Object.values(ranges).map((range, index) => (
        <Box key={index}>
          <h2>{rangeNames[index]}</h2>
          <Box display="flex" gap="16px">
            <RangeDisplay range={range.played} />
            <RangeDisplay range={range.gto} />
          </Box>
        </Box>
      ))}
    </Box>
  );
};

export default RangeContainer;
