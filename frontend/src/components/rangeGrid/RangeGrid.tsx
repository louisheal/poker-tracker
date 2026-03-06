import type { Stats } from "@/models";
import { GridCell } from "./GridCell";
import { generateKeys } from "./utils.ts";

interface Props {
  hands: { [handKey: string]: Stats };
}

export const RangeGrid = (props: Props) => {
  const keys: string[] = generateKeys();

  return (
    <div
      className="grid gap-1.5 w-full p-0"
      style={{ gridTemplateColumns: "repeat(13, minmax(0, 1fr))" }}
    >
      {keys.map((key: string) => {
        const hand = props.hands?.[key] ?? { folds: 0, raises: 0, calls: 0 };

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
