import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { useMemo } from "react";

interface BetSizeDistributionProps {
  sizes: number[];
  title?: string;
}

const BIN_WIDTH = 16;
const MAX_BIN = 200;

function buildDistribution(sizes: number[]) {
  const bins: { pct: number; count: number; density: number }[] = [];
  for (let i = 0; i <= MAX_BIN; i += BIN_WIDTH) {
    bins.push({ pct: i, count: 0, density: 0 });
  }

  const capped = sizes.filter((s) => s <= MAX_BIN + BIN_WIDTH);
  for (const s of capped) {
    const idx = Math.min(Math.floor(s / BIN_WIDTH), bins.length - 1);
    bins[idx].count++;
  }

  const total = capped.length || 1;
  for (const bin of bins) {
    bin.density = (bin.count / total) * 100;
  }
  return bins;
}

const CustomTooltip = ({
  active,
  payload,
  totalCount,
}: {
  active?: boolean;
  payload?: { payload: { pct: number; count: number; density: number } }[];
  totalCount?: number;
}) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const pct = totalCount ? ((d.count / totalCount) * 100).toFixed(1) : "0";
  return (
    <div className="bg-popover border border-border rounded-md px-3 py-2 text-xs shadow-md">
      <p className="font-semibold">
        B{d.pct}–B{d.pct + BIN_WIDTH}
      </p>
      <p className="text-muted-foreground">{pct}% of bets</p>
    </div>
  );
};

export const BetSizeDistribution = ({ sizes, title }: BetSizeDistributionProps) => {
  const data = useMemo(() => buildDistribution(sizes), [sizes]);

  const median = useMemo(() => {
    if (!sizes.length) return 0;
    const sorted = [...sizes].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }, [sizes]);

  if (!sizes.length) {
    return (
      <div className="bg-card border border-border rounded-xl p-6">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">
          {title ?? "Villain C-Bet Size Distribution"}
        </h3>
        <p className="text-xs text-muted-foreground">No bet data available</p>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-4">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          {title ?? "Villain C-Bet Size Distribution"}
        </h3>
        <span className="text-xs text-muted-foreground">
          {sizes.length} bets · median {median.toFixed(0)}% pot
        </span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="betSizeGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ffffff" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#ffffff" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="pct"
            tick={{ fontSize: 10, fill: "#ffffff" }}
            tickFormatter={(v: number) => `${v}%`}
            interval={1}
            stroke="#ffffff40"
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#ffffff" }}
            tickFormatter={(v: number) => `${v.toFixed(0)}%`}
            stroke="#ffffff40"
          />
          <Tooltip content={<CustomTooltip totalCount={sizes.length} />} />
          <ReferenceLine
            x={Math.floor(median / BIN_WIDTH) * BIN_WIDTH}
            stroke="#ffffff"
            strokeDasharray="3 3"
            strokeOpacity={0.3}
          />
          <Area
            type="monotone"
            dataKey="density"
            stroke="#ffffff"
            fill="url(#betSizeGrad)"
            strokeWidth={2}
            animationDuration={300}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
