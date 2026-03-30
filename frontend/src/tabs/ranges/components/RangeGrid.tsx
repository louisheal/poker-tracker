import type { Stats } from "@/models";
import { HandGrid } from "@/common/HandGrid";

interface Props {
  hands: { [handKey: string]: Stats };
}

export const RangeGrid = ({ hands }: Props) => (
  <HandGrid
    cellProps={(key) => {
      const hand = hands?.[key] ?? { folds: 0, raises: 0, calls: 0 };
      return {
        folds: hand.folds,
        raises: hand.raises,
        calls: hand.calls,
      };
    }}
  />
);
