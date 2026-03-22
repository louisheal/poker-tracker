import { useState } from "react";

import type { NextAction } from "@/api";
import { EvRow } from "./EvRow";

const ACTION_LABELS: Record<string, string> = {
  X: "Check",
  B: "Bet",
  C: "Call",
  R: "Raise",
  F: "Fold",
};

const SIZE_LABELS: Record<string, string> = {
  "0-50": "Small (0-50%)",
  "50-100": "Medium (50-100%)",
  "100-200": "Large (100-200%)",
  "200+": "Overbet (200%+)",
};

function parseActionKey(action: string): {
  base: string;
  sizeRange?: [number, number];
  sizeLabel?: string;
} {
  const match = action.match(/^([BRCXF])(\d+-\d+|\d+\+)?$/);
  if (!match) return { base: action };
  const base = match[1];
  const sizePart = match[2];
  if (!sizePart) return { base };
  const sizeLabel = SIZE_LABELS[sizePart] ?? sizePart;
  if (sizePart.endsWith("+")) {
    const lo = parseInt(sizePart.slice(0, -1));
    return { base, sizeRange: [lo, 999], sizeLabel };
  }
  const [lo, hi] = sizePart.split("-").map(Number);
  return { base, sizeRange: [lo, hi], sizeLabel };
}

interface ActionGroup {
  base: string;
  label: string;
  ev: number;
  count: number;
  children: {
    action: NextAction;
    sizeRange?: [number, number];
    sizeLabel?: string;
  }[];
}

function groupActions(nextActions: NextAction[]): ActionGroup[] {
  const groupMap = new Map<string, ActionGroup>();
  const order: string[] = [];

  for (const na of nextActions) {
    const { base, sizeRange, sizeLabel } = parseActionKey(na.action);
    let group = groupMap.get(base);
    if (!group) {
      group = {
        base,
        label: ACTION_LABELS[base] ?? base,
        ev: 0,
        count: 0,
        children: [],
      };
      groupMap.set(base, group);
      order.push(base);
    }
    group.count += na.count;
    group.children.push({ action: na, sizeRange, sizeLabel });
  }

  for (const group of groupMap.values()) {
    if (group.count > 0) {
      group.ev =
        group.children.reduce((sum, c) => sum + c.action.ev * c.action.count, 0) /
        group.count;
    }
  }

  return order.map((key) => groupMap.get(key)!);
}

interface Props {
  nextActor: "hero" | "villain" | "";
  overallEv: number;
  handCount: number;
  nextActions: NextAction[];
  onActionClick: (action: string, sizeRange?: [number, number]) => void;
  showTurnTransition?: boolean;
  onContinueToTurn?: () => void;
  showRiverTransition?: boolean;
  onContinueToRiver?: () => void;
}

export const EvPanel = ({
  nextActor,
  overallEv,
  handCount,
  nextActions,
  onActionClick,
  showTurnTransition,
  onContinueToTurn,
  showRiverTransition,
  onContinueToRiver,
}: Props) => {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const actorLabel = nextActor === "hero" ? "Hero" : "Villain";
  const overallColor =
    overallEv > 0
      ? "text-emerald-400"
      : overallEv < 0
        ? "text-red-400"
        : "text-muted-foreground";

  const groups = groupActions(nextActions);

  const toggleGroup = (base: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(base)) next.delete(base);
      else next.add(base);
      return next;
    });
  };

  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-4">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Expected Value
        </h3>
        <span className="text-xs text-muted-foreground">{handCount} hands</span>
      </div>

      <div className="bg-background/50 border border-border rounded-lg px-4 py-3 flex items-center justify-between">
        <span className="text-sm font-semibold">Overall</span>
        <span className={`text-lg font-bold tabular-nums ${overallColor}`}>
          {overallEv > 0 ? "+" : ""}
          {overallEv.toFixed(1)} BB
        </span>
      </div>

      <div className="flex flex-col divide-y divide-border">
        {groups.map((group) => {
          const isSized = group.children.length > 1;
          const isExpanded = expandedGroups.has(group.base);

          if (!isSized) {
            const child = group.children[0];
            return (
              <EvRow
                key={group.base}
                label={`${actorLabel} ${group.label}${child.sizeLabel ? ` ${child.sizeLabel}` : ""}`}
                evBb={group.ev}
                count={group.count}
                onClick={() => onActionClick(group.base, child.sizeRange)}
              />
            );
          }

          return (
            <div key={group.base}>
              <EvRow
                label={`${actorLabel} ${group.label}`}
                evBb={group.ev}
                count={group.count}
                onClick={() => onActionClick(group.base)}
                expandable
                expanded={isExpanded}
                onToggleExpand={() => toggleGroup(group.base)}
              />
              {isExpanded &&
                group.children.map((child) => (
                  <EvRow
                    key={child.action.action}
                    label={child.sizeLabel ?? child.action.action}
                    evBb={child.action.ev}
                    count={child.action.count}
                    onClick={() => onActionClick(group.base, child.sizeRange)}
                    indented
                  />
                ))}
            </div>
          );
        })}
        {nextActions.length === 0 && showTurnTransition && (
          <button
            onClick={onContinueToTurn}
            className="text-sm font-medium text-primary hover:underline py-2 text-left"
          >
            Continue to Turn →
          </button>
        )}
        {nextActions.length === 0 && showRiverTransition && (
          <button
            onClick={onContinueToRiver}
            className="text-sm font-medium text-primary hover:underline py-2 text-left"
          >
            Continue to River →
          </button>
        )}
        {nextActions.length === 0 && !showTurnTransition && !showRiverTransition && (
          <p className="text-xs text-muted-foreground py-2">
            No further actions (hand complete)
          </p>
        )}
      </div>
    </div>
  );
};
