export const generateKeys = () => {
  const ranks = [
    "A",
    "K",
    "Q",
    "J",
    "T",
    "9",
    "8",
    "7",
    "6",
    "5",
    "4",
    "3",
    "2",
  ];
  let keys: string[] = [];
  for (const a of ranks) {
    let passed = false;
    for (const b of ranks) {
      if (a === b) {
        passed = true;
        keys = keys.concat(`${a}${b}`);
      } else if (passed) {
        keys = keys.concat(`${a}${b}s`);
      } else {
        keys = keys.concat(`${b}${a}o`);
      }
    }
  }
  return keys;
};

export default generateKeys;
