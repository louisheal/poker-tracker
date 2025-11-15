import type { HandDto } from "./domain";

export const fetchHand = async (): Promise<HandDto> => {
  const data = await fetch("http://localhost:8000/hand");
  const hand = await data.json();
  return hand;
};

export const raiseHand = async (id: string) => {
  await fetch(`http://localhost:8000/hand/${id}/raise`, { method: "POST" });
};

export const foldHand = async (id: string) => {
  await fetch(`http://localhost:8000/hand/${id}/fold`, { method: "POST" });
};
