import type { BoardTypeFilter, PotTypeFilter, CbetStats, Ranges } from "./models";

export const getRanges = async () => {
  const response = await fetch("http://localhost:8000");
  const rangeResponse: Ranges = await response.json();
  return rangeResponse;
};

export const getCbets = async (
  heroInPosition: boolean[],
  heroPfr: boolean[],
  boardTypes: BoardTypeFilter[],
  potTypes: PotTypeFilter[]
): Promise<CbetStats> => {
  const params = new URLSearchParams();
  for (const value of heroInPosition) {
    params.append("hero_in_position", String(value));
  }
  for (const value of heroPfr) {
    params.append("hero_preflop_raiser", String(value));
  }
  for (const value of boardTypes) {
    params.append("board_types", value);
  }
  for (const value of potTypes) {
    params.append("pot_types", value);
  }
  const response = await fetch(`http://localhost:8000/cbets?${params}`);
  return response.json();
};
