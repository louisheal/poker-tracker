import type { Ranges } from "./models";

export const getRanges = async () => {
  const response = await fetch("http://localhost:8000");
  const rangeResponse: Ranges = await response.json();
  return rangeResponse;
};
