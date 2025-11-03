import type { HandDto } from "./domain";

export const fetchHand = async (): Promise<HandDto> => {
  const data = await fetch("http://localhost:8000/hand");
  const hand = await data.json();
  return hand;
};
