import type { ActionLine as ActionLineType } from "@/models";
import { ActionTag } from "./ActionTag";

interface Props {
  actionLine: ActionLineType;
  onClickFlop: () => void;
  onClickTag: (index: number) => void;
  onRemoveLast: () => void;
}

export const ActionLine = ({ actionLine, onClickFlop, onClickTag, onRemoveLast }: Props) => {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {/* Flop - cursor = -1 means at flop */}
      <ActionTag
        label="Flop"
        isActive={actionLine.cursor === -1}
        isFuture={false}
        onClick={onClickFlop}
        showArrow={false}
      />

      {/* Action tags */}
      {actionLine.actions.map((la, i) => {
        const isActive = i === actionLine.cursor;
        const isFuture = i > actionLine.cursor;
        return (
          <ActionTag
            key={i}
            label={la.label}
            isActive={isActive}
            isFuture={isFuture}
            onClick={() => onClickTag(i)}
            onRemove={i === actionLine.actions.length - 1 ? onRemoveLast : undefined}
            showArrow={true}
          />
        );
      })}
    </div>
  );
};
