import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { DailyVolumePoint, DateRangeFilter } from "@/models";

interface DateRangeDockProps {
  points: DailyVolumePoint[];
  value: DateRangeFilter;
  onChange: (value: DateRangeFilter) => void;
}

type DragMode = "start" | "end" | "window" | null;

const clamp = (value: number, min: number, max: number): number => {
  if (value < min) {
    return min;
  }
  if (value > max) {
    return max;
  }
  return value;
};

export const DateRangeDock = ({
  points,
  value,
  onChange,
}: DateRangeDockProps) => {
  const allDays = useMemo(() => {
    if (!points.length) {
      return [] as DailyVolumePoint[];
    }

    const sorted = [...points].sort((a, b) => a.date.localeCompare(b.date));
    const firstDate = new Date(`${sorted[0].date}T00:00:00`);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const byDate = new Map(sorted.map((point) => [point.date, point.count]));
    const filled: DailyVolumePoint[] = [];

    const d = new Date(firstDate);
    while (d <= today) {
      const iso = d.toISOString().slice(0, 10);
      filled.push({ date: iso, count: byDate.get(iso) ?? 0 });
      d.setDate(d.getDate() + 1);
    }

    return filled;
  }, [points]);

  const lastIndex = Math.max(allDays.length - 1, 0);
  const maxCount = Math.max(1, ...allDays.map((day) => day.count), 1);

  const dateToIndex = useMemo(() => {
    return new Map(allDays.map((day, i) => [day.date, i]));
  }, [allDays]);

  const chartRef = useRef<HTMLDivElement | null>(null);

  const externalStartIndex =
    value.startDate && dateToIndex.has(value.startDate)
      ? dateToIndex.get(value.startDate)!
      : 0;
  const externalEndIndex =
    value.endDate && dateToIndex.has(value.endDate)
      ? dateToIndex.get(value.endDate)!
      : lastIndex;

  const [startIndex, setStartIndex] = useState(externalStartIndex);
  const [endIndex, setEndIndex] = useState(externalEndIndex);
  const [dragMode, setDragMode] = useState<DragMode>(null);
  const [dragOffset, setDragOffset] = useState(0);

  const baselineStart = Math.min(externalStartIndex, externalEndIndex);
  const baselineEnd = Math.max(externalStartIndex, externalEndIndex);
  const activeStart = dragMode ? startIndex : baselineStart;
  const activeEnd = dragMode ? endIndex : baselineEnd;

  const emitRange = useCallback(
    (s: number, e: number) => {
      if (!allDays.length) {
        return;
      }
      const nextStart = clamp(Math.min(s, e), 0, lastIndex);
      const nextEnd = clamp(Math.max(s, e), 0, lastIndex);
      setStartIndex(nextStart);
      setEndIndex(nextEnd);
      onChange({
        startDate: allDays[nextStart].date,
        endDate: allDays[nextEnd].date,
      });
    },
    [allDays, lastIndex, onChange],
  );

  const indexFromClientX = useCallback(
    (clientX: number) => {
      const rect = chartRef.current?.getBoundingClientRect();
      if (!rect || rect.width <= 0) {
        return 0;
      }
      const ratio = clamp((clientX - rect.left) / rect.width, 0, 1);
      return clamp(Math.round(ratio * lastIndex), 0, lastIndex);
    },
    [lastIndex],
  );

  useEffect(() => {
    if (!dragMode) {
      return;
    }

    const onMove = (e: MouseEvent) => {
      const idx = indexFromClientX(e.clientX);

      if (dragMode === "start") {
        emitRange(Math.min(idx, activeEnd), activeEnd);
        return;
      }

      if (dragMode === "end") {
        emitRange(activeStart, Math.max(idx, activeStart));
        return;
      }

      const width = activeEnd - activeStart;
      let nextStart = idx - dragOffset;
      nextStart = clamp(nextStart, 0, Math.max(lastIndex - width, 0));
      emitRange(nextStart, nextStart + width);
    };

    const onUp = () => {
      setDragMode(null);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [
    activeEnd,
    activeStart,
    dragMode,
    dragOffset,
    emitRange,
    indexFromClientX,
    lastIndex,
  ]);

  if (!allDays.length) {
    return (
      <div className="border-t border-border bg-card/90 px-6 py-4">
        <div className="text-xs text-muted-foreground">
          No hand volume data available.
        </div>
      </div>
    );
  }

  const normalizedStart = clamp(activeStart, 0, lastIndex);
  const normalizedEnd = clamp(activeEnd, normalizedStart, lastIndex);
  const selectedLabel = `${allDays[normalizedStart].date} to ${allDays[normalizedEnd].date}`;

  const totalBars = allDays.length;
  const leftPct = (normalizedStart / totalBars) * 100;
  const widthPct = ((normalizedEnd - normalizedStart + 1) / totalBars) * 100;

  return (
    <div className="border-t border-border bg-card/90 px-6 py-4">
      <div className="flex w-full flex-col gap-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Volume
          </span>
          <span className="text-xs text-muted-foreground">{selectedLabel}</span>
        </div>

        <div className="relative rounded-md border border-border bg-background/50 px-3 py-3">
          <div ref={chartRef} className="relative h-24">
            <div className="absolute inset-0 flex items-end gap-0.5">
              {allDays.map((day) => {
                const height = (day.count / maxCount) * 100;
                return (
                  <div
                    key={day.date}
                    className="group relative flex h-full min-w-0 flex-1 items-end"
                  >
                    <div
                      className="w-4 rounded-sm bg-primary/80"
                      style={{ height: `${height}%` }}
                    />
                    <div className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-1 -translate-x-1/2 whitespace-nowrap rounded-md border border-border bg-card px-2 py-1 text-[11px] text-foreground opacity-0 shadow-sm transition-opacity group-hover:opacity-100">
                      {day.date} - {day.count} hands
                    </div>
                  </div>
                );
              })}
            </div>

            <div
              className="absolute inset-y-0 rounded-md border border-primary bg-primary/15"
              style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
            >
              <div
                className="absolute inset-0 cursor-grab active:cursor-grabbing"
                onMouseDown={(e) => {
                  setStartIndex(baselineStart);
                  setEndIndex(baselineEnd);
                  const idx = indexFromClientX(e.clientX);
                  setDragMode("window");
                  setDragOffset(idx - normalizedStart);
                }}
              />
              <div
                className="absolute inset-y-0 left-0 w-2 cursor-ew-resize rounded-l-md bg-primary/70"
                onMouseDown={(e) => {
                  e.stopPropagation();
                  setStartIndex(baselineStart);
                  setEndIndex(baselineEnd);
                  setDragMode("start");
                }}
              />
              <div
                className="absolute inset-y-0 right-0 w-2 cursor-ew-resize rounded-r-md bg-primary/70"
                onMouseDown={(e) => {
                  e.stopPropagation();
                  setStartIndex(baselineStart);
                  setEndIndex(baselineEnd);
                  setDragMode("end");
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
