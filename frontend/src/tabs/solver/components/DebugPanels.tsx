import { useState } from "react";
import type { SolverDebug } from "@/models";
import type { ActionOption } from "../types";
import { HandGrid as SharedHandGrid } from "@/common/HandGrid";

interface Props {
  debug: SolverDebug;
  actionOptions: ActionOption[];
}

interface RangePanelProps {
  label: string;
  range: Record<string, number>;
}

const RangePanel = ({ label, range }: RangePanelProps) => {
  const [open, setOpen] = useState(true);
  const handCount = Object.keys(range).length;

  return (
    <div className="p-3 rounded-lg border border-border bg-card space-y-2">
      <button
        className="flex items-center gap-1.5 w-full text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-xs text-muted-foreground">
          {open ? "v" : ">"}
        </span>
        <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          {label} -- {handCount} hands
        </h4>
      </button>
      {open && (
        <SharedHandGrid
          cellProps={(key) => {
            const freq = range[key];
            if (freq === undefined || freq === 0) return {};
            return {
              colour: "bg-sky-600 text-white",
              title: `${key}: ${(freq * 100).toFixed(0)}%`,
              bgOpacity: freq,
            };
          }}
        />
      )}
    </div>
  );
};

export const DebugPanels = ({ debug, actionOptions }: Props) => {
  const [modelOpen, setModelOpen] = useState(true);

  return (
    <div className="space-y-4">
      {/* Pot & Sizing Info */}
      <div className="p-3 rounded-lg border border-border bg-card space-y-1">
        <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Pot & Sizing
        </h4>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
          <div className="text-muted-foreground">Pot</div>
          <div className="text-foreground font-mono">{debug.potBB?.toFixed(2) ?? "—"} BB</div>
          {debug.callAmountBB > 0 && (
            <>
              <div className="text-muted-foreground">Call amount</div>
              <div className="text-foreground font-mono">{debug.callAmountBB.toFixed(2)} BB</div>
            </>
          )}
          <div className="text-muted-foreground">Eff. stack</div>
          <div className="text-foreground font-mono">{debug.effectiveStackBB?.toFixed(0) ?? "—"} BB</div>
          <div className="text-muted-foreground">SPR</div>
          <div className="text-foreground font-mono">
            {debug.potBB > 0 ? (debug.effectiveStackBB / debug.potBB).toFixed(1) : "—"}
          </div>
        </div>
      </div>

      {/* OOP Range */}
      <RangePanel
        label={debug.oopPosition}
        range={debug.oopRange}
      />

      {/* IP Range */}
      <RangePanel
        label={debug.ipPosition}
        range={debug.ipRange}
      />

      {/* Model Output */}
      <div className="p-3 rounded-lg border border-border bg-card space-y-3">
        <button
          className="flex items-center gap-1.5 w-full text-left"
          onClick={() => setModelOpen((v) => !v)}
        >
          <span className="text-xs text-muted-foreground">
            {modelOpen ? "v" : ">"}
          </span>
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Model Output
          </h4>
        </button>
        {modelOpen &&
          actionOptions.map((opt) => {
            const data = debug.modelOutput[opt.key];
            if (!data) return null;
            return (
              <div key={opt.key} className="space-y-1">
                <span className="text-xs font-medium text-foreground">
                  {opt.label}
                  {data.bet_size_bb > 0 && (
                    <span className="text-muted-foreground font-mono ml-2">
                      {data.bet_size_bb.toFixed(1)} BB ({data.bet_size_pct_pot.toFixed(0)}% pot)
                    </span>
                  )}
                </span>
                <div className="grid grid-cols-3 gap-x-3 gap-y-0.5 text-xs">
                  <div className="text-muted-foreground">Opp folds</div>
                  <div className="text-foreground font-mono">
                    {data.villain_fold_pct}%
                  </div>
                  <div className="text-muted-foreground/50 font-mono">
                    raw: {data.raw_fold.toFixed(3)}
                  </div>

                  <div className="text-muted-foreground">Opp calls</div>
                  <div className="text-foreground font-mono">
                    {data.villain_call_pct}%
                  </div>
                  <div className="text-muted-foreground/50 font-mono">
                    chk: {data.raw_check.toFixed(3)} call:{" "}
                    {data.raw_call.toFixed(3)}
                  </div>

                  <div className="text-muted-foreground">Opp raises</div>
                  <div className="text-foreground font-mono">
                    {data.villain_raise_pct}%
                  </div>
                  <div className="text-muted-foreground/50 font-mono">
                    bet: {data.raw_bet.toFixed(3)} raise:{" "}
                    {data.raw_raise.toFixed(3)}
                  </div>
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
};
