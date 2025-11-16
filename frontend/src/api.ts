import type { HandDto, Ranges } from "./domain";

export const fetchHand = async (): Promise<HandDto> => {
  const data = await fetch("http://localhost:8000/hand");
  const hand = await data.json();
  return hand;
};

export const raiseHand = async (id: string, pos: number): Promise<boolean> => {
  interface RaiseResult {
    correct: boolean;
  }

  const response = await fetch(`http://localhost:8000/hand/${id}/raise`, {
    method: "POST",
    body: JSON.stringify({ pos: pos }),
    headers: {
      "Content-Type": "application/json",
    },
  });

  const result: RaiseResult = await response.json();
  return result.correct;
};

export const foldHand = async (id: string, pos: number): Promise<boolean> => {
  interface FoldResult {
    correct: boolean;
  }

  const response = await fetch(`http://localhost:8000/hand/${id}/fold`, {
    method: "POST",
    body: JSON.stringify({ pos: pos }),
    headers: {
      "Content-Type": "application/json",
    },
  });

  const result: FoldResult = await response.json();
  return result.correct;
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
