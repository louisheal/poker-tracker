import type { RfiRanges } from "./models";

export const getRanges = async () => {
  const response = await fetch("http://localhost:8000");
  const rangeResponse: RfiRanges = await response.json();
  return rangeResponse;
};
