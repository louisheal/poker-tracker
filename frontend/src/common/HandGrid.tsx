import { generateHandKeys } from "./handKeys";
import { GridCell } from "./GridCell";

const HAND_KEYS = generateHandKeys();

interface Props {
  /** Render function to provide cell props for each hand key */
  cellProps: (handKey: string) => {
    folds?: number;
    raises?: number;
    calls?: number;
    colour?: string;
    onClick?: () => void;
    isSelected?: boolean;
    title?: string;
  };
}

export const HandGrid = ({ cellProps }: Props) => (
  <div
    className="grid gap-1.5 w-full"
    style={{ gridTemplateColumns: "repeat(13, minmax(0, 1fr))" }}
  >
    {HAND_KEYS.map((key) => (
      <GridCell key={key} handKey={key} {...cellProps(key)} />
    ))}
  </div>
);
