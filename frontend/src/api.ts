import type { RangeResponse } from "./models";

export const getRanges = async () => {
  const response = await fetch("http://localhost:8000");
  const rangeResponse: RangeResponse = await response.json();
  return rangeResponse;
};
