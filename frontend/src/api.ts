import type { HandDto } from "./domain";

export const fetchHand = async (): Promise<HandDto> => {
  const data = await fetch("http://localhost:8000/hand");
  const hand = await data.json();
  return hand;
};

export const raiseHand = async (): Promise<HandDto> => {
  const data = await fetch("http://localhost:8000/raise", { method: "POST" });
  const hand = await data.json();
  return hand;
};

export const foldHand = async (): Promise<HandDto> => {
  const data = await fetch("http://localhost:8000/fold", { method: "POST" });
  const hand = await data.json();
  return hand;
};
