import { Button } from "@/components/ui/button";

type Option = {
  key: string;
  label: string;
  active: boolean;
};

type Props = {
  options: Option[];
  onToggle: (key: string) => void;
  className?: string;
};

export const FilterGroup = ({ options, onToggle, className }: Props) => {
  return (
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
};

export default FilterGroup;
