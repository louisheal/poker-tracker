import type { Stats } from "@/models";
import { GridCell } from "./GridCell";

const generateKeys = () => {
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

interface Props {
  hands: { [handKey: string]: Stats };
}

export const RangeGrid = (props: Props) => {
  const keys = generateKeys();

  return (
    <div className="flex flex-wrap w-2xl justify-self-center">
      {keys.map((key) => {
        const hand = props.hands[key];

        return (
          <GridCell
            key={key}
            handKey={key}
            folds={hand.folds}
            raises={hand.raises}
            calls={hand.calls}
          />
        );
      })}
    </div>
  );
};
