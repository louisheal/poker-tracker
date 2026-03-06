import "./App.css";

import { useState } from "react";
import { BarChart2, Grid2x2 } from "lucide-react";
import { ThemeProvider } from "@/components/theme-provider";
import { cn } from "@/lib/utils";
import { RangeView } from "./views/RangeView";
import { CbetView } from "./views/CbetView";

type View = "ranges" | "cbets";

const NAV_ITEMS = [
  { id: "ranges" as View, label: "Ranges", icon: Grid2x2 },
  { id: "cbets" as View, label: "C-Bets", icon: BarChart2 },
];

function App() {
  const [view, setView] = useState<View>("ranges");

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
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </nav>
        <main className="flex-1 overflow-auto">
          {view === "ranges" ? <RangeView /> : <CbetView />}
        </main>
      </div>
    </ThemeProvider>
  );
}

export default App;
