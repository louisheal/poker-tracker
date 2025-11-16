import type { HandDto, Ranges } from "./domain";

export const fetchHand = async (): Promise<HandDto> => {
  const data = await fetch("http://localhost:8000/hand");
  const hand = await data.json();
  return hand;
};

export const raiseHand = async (id: string, pos: number) => {
  console.log(JSON.stringify({ pos: pos }));
  await fetch(`http://localhost:8000/hand/${id}/raise`, {
    method: "POST",
    body: JSON.stringify({ pos: pos }),
    headers: {
      "Content-Type": "application/json",
    },
  });
};

export const foldHand = async (id: string, pos: number) => {
  await fetch(`http://localhost:8000/hand/${id}/fold`, {
    method: "POST",
    body: JSON.stringify({ pos: pos }),
    headers: {
      "Content-Type": "application/json",
    },
  });
};

export const fetchRange = async (pos: number): Promise<Ranges> => {
  const data = await fetch("http://localhost:8000/range", {
    method: "POST",
    body: JSON.stringify({ pos: pos }),
    headers: {
      "Content-Type": "application/json",
    },
  });
  const range = await data.json();
  return range;
};
