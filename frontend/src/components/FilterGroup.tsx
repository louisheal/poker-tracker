import { Button } from "@/components/ui/button";

interface Props {
  options: { key: string; label: string; active: boolean }[];
  onToggle: (key: string) => void;
  className?: string;
}

export const FilterGroup = ({ options, onToggle, className }: Props) => (
  <div className={className ?? "flex items-center gap-2"}>
    {options.map((opt) => (
      <Button
        key={opt.key}
        variant={opt.active ? "outline" : "default"}
        onClick={() => onToggle(opt.key)}
      >
        {opt.label}
      </Button>
    ))}
  </div>
);

export default FilterGroup;
