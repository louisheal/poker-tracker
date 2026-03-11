import "./App.css";

import { useEffect, useState } from "react";
import { BarChart2, Grid2x2, TrendingUp } from "lucide-react";
import { ThemeProvider } from "@/components/theme-provider";
import { cn } from "@/lib/utils";
import { RangeView } from "./views/RangeView";
import { CbetView } from "./views/CbetView";
import { TurnView } from "./views/TurnView";
import { DateRangeDock } from "./components/DateRangeDock";
import { getHandVolume } from "./api";
import type { DailyVolumePoint, DateRangeFilter } from "./models";

type View = "ranges" | "flop" | "turn";

const NAV_ITEMS = [
  { id: "ranges" as View, label: "Ranges", icon: Grid2x2 },
  { id: "flop" as View, label: "Flop", icon: BarChart2 },
  { id: "turn" as View, label: "Turn", icon: TrendingUp },
];

function App() {
  const [view, setView] = useState<View>("ranges");
  const [handVolume, setHandVolume] = useState<DailyVolumePoint[]>([]);
  const [dateRange, setDateRange] = useState<DateRangeFilter>({});

  useEffect(() => {
    const loadHandVolume = async () => {
      const points = await getHandVolume();
      setHandVolume(points);
      if (!points.length) {
        return;
      }
      setDateRange((prev) => {
        if (prev.startDate || prev.endDate) {
          return prev;
        }
        return {
          startDate: points[0].date,
          endDate: points[points.length - 1].date,
        };
      });
    };

    loadHandVolume();
  }, []);

  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <div className="flex h-screen bg-background text-foreground overflow-hidden">
        <nav className="w-48 shrink-0 border-r border-border flex flex-col py-6 gap-1">
          <span className="px-4 pb-4 text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            Poker Tracker
          </span>
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setView(id)}
              className={cn(
                "flex items-center gap-3 px-4 py-2 mx-2 rounded-md text-sm transition-colors",
                view === id
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50",
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </nav>
        <div className="flex min-w-0 flex-1 flex-col">
          <main className="min-h-0 flex-1 overflow-auto">
            {view === "ranges" ? (
              <RangeView dateRange={dateRange} />
            ) : view === "flop" ? (
              <CbetView dateRange={dateRange} />
            ) : (
              <TurnView dateRange={dateRange} />
            )}
          </main>
          <DateRangeDock
            points={handVolume}
            value={dateRange}
            onChange={setDateRange}
          />
        </div>
      </div>
    </ThemeProvider>
  );
}

export default App;
