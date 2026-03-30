const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];

/**
 * Generate all 169 hand keys in row-major order for a 13x13 grid.
 * Diagonal = pairs, above = suited, below = offsuit.
 */
export const generateHandKeys = (): string[] => {
  const keys: string[] = [];
  for (let row = 0; row < RANKS.length; row++) {
    for (let col = 0; col < RANKS.length; col++) {
      const a = RANKS[row];
      const b = RANKS[col];
      if (row === col) {
        keys.push(`${a}${b}`);
      } else if (row < col) {
        keys.push(`${a}${b}s`);
      } else {
        keys.push(`${b}${a}o`);
      }
    }
  }
  return keys;
};
