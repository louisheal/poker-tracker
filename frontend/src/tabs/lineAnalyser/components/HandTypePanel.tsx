import { useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { PlayerHandTypes, MadeHandType, DrawType } from "@/models";

const MADE_HAND_LABELS: Record<MadeHandType, string> = {
  STRAIGHT_FLUSH: "Straight Flush",
  QUADS: "Quads",
  FULL_HOUSE: "Full House",
  FLUSH: "Flush",
  STRAIGHT: "Straight",
  SET: "Set / Trips",
  TWO_PAIR: "Two Pair",
  OVERPAIR: "Overpair",
  TOP_PAIR: "Top Pair",
  PAIR: "Pair",
  ACE_HIGH: "A High",
  NO_MADE_HAND: "No Made Hand",
};

const DRAW_LABELS: Record<DrawType, string> = {
  FLUSH_OESD: "Flush + OESD",
  FLUSH_GUTSHOT: "Flush + Gutshot",
  FLUSH_DRAW: "Flush Draw",
  OESD: "OESD",
  GUTSHOT: "Gutshot",
  NO_DRAW: "No Draw",
};

const MADE_HAND_COLORS: Record<MadeHandType, string> = {
  STRAIGHT_FLUSH: "#ff0040",
  QUADS: "#ff4400",
  FULL_HOUSE: "#ff8800",
  FLUSH: "#00aaff",
  STRAIGHT: "#aa44ff",
  SET: "#00dd55",
  TWO_PAIR: "#00eebb",
  OVERPAIR: "#dd00ff",
  TOP_PAIR: "#ff55aa",
  PAIR: "#ffaa00",
  ACE_HIGH: "#88ccff",
  NO_MADE_HAND: "#667788",
};

const DRAW_COLORS: Record<DrawType, string> = {
  FLUSH_OESD: "#ff2266",
  FLUSH_GUTSHOT: "#ff6600",
  FLUSH_DRAW: "#00bbff",
  OESD: "#ffcc00",
  GUTSHOT: "#44dd00",
  NO_DRAW: "#667788",
};

const MADE_HAND_ORDER: MadeHandType[] = [
  "STRAIGHT_FLUSH",
  "QUADS",
  "FULL_HOUSE",
  "FLUSH",
  "STRAIGHT",
  "SET",
  "TWO_PAIR",
  "OVERPAIR",
  "TOP_PAIR",
  "PAIR",
  "ACE_HIGH",
  "NO_MADE_HAND",
];

const DRAW_ORDER: DrawType[] = [
  "FLUSH_OESD",
  "FLUSH_GUTSHOT",
  "FLUSH_DRAW",
  "OESD",
  "GUTSHOT",
  "NO_DRAW",
];

interface ChartEntry {
  name: string;
  value: number;
  color: string;
}

function buildChartData<T extends string>(
  distribution: Record<T, number>,
  labels: Record<T, string>,
  colors: Record<T, string>,
  order: T[],
): ChartEntry[] {
  return order
    .filter((key) => distribution[key] > 0)
    .map((key) => ({
      name: labels[key],
      value: distribution[key],
      color: colors[key],
    }));
}

const ChartTooltip = ({
  active,
  payload,
  totalCount,
}: {
  active?: boolean;
  payload?: { payload: ChartEntry }[];
  totalCount: number;
}) => {
  if (!active || !payload?.length) return null;
  const entry = payload[0].payload;
  const pct = totalCount > 0 ? ((entry.value / totalCount) * 100).toFixed(1) : "0";
  return (
    <div className="bg-popover border border-border rounded-md px-3 py-2 text-xs shadow-md">
      <p className="font-semibold">{entry.name}</p>
      <p className="text-muted-foreground">
        {entry.value} hands ({pct}%)
      </p>
    </div>
  );
};

interface MiniPieProps {
  title: string;
  data: ChartEntry[];
  totalCount: number;
}

const MiniPie = ({ title, data, totalCount }: MiniPieProps) => {
  if (totalCount === 0) {
    return (
      <div className="flex flex-col gap-2 flex-1 min-w-0">
        <h4 className="text-xs font-medium text-muted-foreground">{title}</h4>
        <p className="text-xs text-muted-foreground">No data</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 flex-1 min-w-0">
      <h4 className="text-xs font-medium text-muted-foreground">{title}</h4>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={65}
            innerRadius={42}
            strokeWidth={1}
            stroke="#1e293b"
            animationDuration={300}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltip totalCount={totalCount} />} />
          <Legend
            layout="vertical"
            align="right"
            verticalAlign="middle"
            iconSize={8}
            wrapperStyle={{ fontSize: "10px", lineHeight: "16px" }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

interface HandTypePanelProps {
  title: string;
  distribution: PlayerHandTypes | null;
}

export const HandTypePanel = ({ title, distribution }: HandTypePanelProps) => {
  const madeHandData = useMemo(() => {
    if (!distribution) return [];
    return buildChartData(
      distribution.made_hands,
      MADE_HAND_LABELS,
      MADE_HAND_COLORS,
      MADE_HAND_ORDER,
    );
  }, [distribution]);

  const drawData = useMemo(() => {
    if (!distribution) return [];
    return buildChartData(
      distribution.draws,
      DRAW_LABELS,
      DRAW_COLORS,
      DRAW_ORDER,
    );
  }, [distribution]);

  const madeTotal = useMemo(
    () => madeHandData.reduce((sum, d) => sum + d.value, 0),
    [madeHandData],
  );

  const drawTotal = useMemo(
    () => drawData.reduce((sum, d) => sum + d.value, 0),
    [drawData],
  );

  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-4">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          {title}
        </h3>
        <span className="text-xs text-muted-foreground">
          {madeTotal} hands
        </span>
      </div>
      <div className="flex gap-4">
        <MiniPie title="Made Hands" data={madeHandData} totalCount={madeTotal} />
        <MiniPie title="Draws" data={drawData} totalCount={drawTotal} />
      </div>
    </div>
  );
};
