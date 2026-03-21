import { Button } from "@/components/ui/button";

interface Props {
  options: { key: string; label: string }[];
  selected: string;
  onSelect: (key: string) => void;
}

export const RadioFilter = ({ options, selected, onSelect }: Props) => (
  <div className="flex items-center gap-2">
    {options.map((opt) => (
      <Button
        key={opt.key}
        variant={selected === opt.key ? "outline" : "default"}
        onClick={() => onSelect(opt.key)}
      >
        {opt.label}
      </Button>
    ))}
  </div>
);
