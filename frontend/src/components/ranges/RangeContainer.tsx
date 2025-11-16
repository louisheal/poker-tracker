import { useEffect, useState } from "react";
import { fetchRange } from "../../api";
import RangeDisplay from "./RangeDisplay";
import type { Ranges } from "../../domain";
import { Box } from "@mui/material";

interface Props {
  pos: number;
}

const RangeContainer = (props: Props) => {
  const [ranges, setRanges] = useState<Ranges | undefined>();

  useEffect(() => {
    const getRanges = async () => {
      const data = await fetchRange(props.pos);
      setRanges(data);
    };

    getRanges();
  }, [props.pos]);

  if (ranges === undefined) {
    return <></>;
  }

  return (
    <Box display="flex" margin="16px" gap="16px">
      <RangeDisplay range={ranges.played} />
      <RangeDisplay range={ranges.gto} />
    </Box>
  );
};

export default RangeContainer;
