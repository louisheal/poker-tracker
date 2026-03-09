import { getRanges } from "@/api";
import RangeGrid, { GridSkeleton, RangeLegend } from "@/components/rangeGrid";
import { FilterGroup } from "@/components/FilterGroup";
import type { DateRangeFilter, Ranges } from "@/models";
import { useEffect, useState } from "react";

type Positions = "LJ" | "HJ" | "CO" | "BTN" | "SB" | "BB";
type PotType = "SRP" | "THREE_BET" | "FOUR_BET";

const INIT_POS = "LJ";
const INIT_TYPE = "SRP";

const POSITIONS: Record<PotType, { value: Positions; label: string }[]> = {
  SRP: [
    { value: "LJ", label: "LJ" },
    { value: "HJ", label: "HJ" },
    { value: "CO", label: "CO" },
    { value: "BTN", label: "BTN" },
    { value: "SB", label: "SB" },
  ],
  THREE_BET: [
    { value: "LJ", label: "v LJ" },
    { value: "HJ", label: "v HJ" },
    { value: "CO", label: "v CO" },
    { value: "BTN", label: "v BTN" },
    { value: "SB", label: "v SB" },
  ],
  FOUR_BET: [
    { value: "LJ", label: "LJ" },
    { value: "HJ", label: "HJ" },
    { value: "CO", label: "CO" },
    { value: "BTN", label: "BTN" },
    { value: "SB", label: "SB" },
  ],
};

interface RangeViewProps {
  dateRange: DateRangeFilter;
}

export const RangeView = ({ dateRange }: RangeViewProps) => {
  const [ranges, setRanges] = useState<Ranges>();
  const [selectedRange, setSelectedRange] = useState<Positions>(INIT_POS);
  const [potType, setPotType] = useState<PotType>(INIT_TYPE);

  useEffect(() => {
    const loadRanges = async () => {
      const ranges = await getRanges(dateRange.startDate, dateRange.endDate);
      setRanges(ranges);
    };

    loadRanges();
  }, [dateRange.endDate, dateRange.startDate]);

  return (
    <div className="p-8 h-full flex flex-col gap-3">
      <div className="w-full flex">
        <div className="w-full max-w-3xl flex flex-row justify-between items-end">
          <div className="flex flex-col gap-3">
            <FilterGroup
              options={[
                { key: "SRP", label: "SRP", active: potType === "SRP" },
                {
                  key: "THREE_BET",
                  label: "3BET",
                  active: potType === "THREE_BET",
                },
                {
                  key: "FOUR_BET",
                  label: "4BET",
                  active: potType === "FOUR_BET",
                },
              ]}
              onToggle={(k) => setPotType(k as PotType)}
            />
            <FilterGroup
              options={POSITIONS[potType].map((p) => ({
                key: p.value,
                label: p.label,
                active: selectedRange === p.value,
              }))}
              onToggle={(k) => setSelectedRange(k as Positions)}
            />
          </div>
          <RangeLegend />
        </div>
      </div>
      <div className="max-w-3xl">
        {ranges ? (
          <RangeGrid hands={ranges[potType][selectedRange]} />
        ) : (
          <GridSkeleton />
        )}
      </div>
    </div>
  );
};
