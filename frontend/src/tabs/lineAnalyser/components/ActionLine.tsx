import type { ActionLine as ActionLineType } from "@/models";
import { ActionTag } from "./ActionTag";

interface Props {
  actionLine: ActionLineType;
  onClickFlop: () => void;
  onClickTag: (index: number) => void;
  onRemoveLast: () => void;
}

export const ActionLine = ({
  actionLine,
  onClickFlop,
  onClickTag,
  onRemoveLast,
}: Props) => {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {/* Flop - cursor 0 */}
      <ActionTag
        label="Flop"
        isActive={actionLine.cursor === 0}
        isFuture={false}
        onClick={onClickFlop}
        showArrow={false}
      />

      {/* Action tags - cursor 1+ */}
      {actionLine.actions.map((lineAction, i) => {
        const actionCursor = i + 1;
        const isActive = actionCursor === actionLine.cursor;
        const isFuture = actionCursor > actionLine.cursor;
        return (
          <ActionTag
            key={i}
            label={lineAction.label}
            isActive={isActive}
            isFuture={isFuture}
            onClick={() => onClickTag(actionCursor)}
            onRemove={
              i === actionLine.actions.length - 1 ? onRemoveLast : undefined
            }
            showArrow={true}
          />
        );
      })}
    </div>
  );
};
