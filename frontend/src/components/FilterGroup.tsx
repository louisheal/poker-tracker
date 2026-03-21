import { Button } from "@/components/ui/button";

type ToggleProps = {
  radio?: false;
  options: { key: string; label: string; active: boolean }[];
  onToggle: (key: string) => void;
  className?: string;
};

type RadioProps = {
  radio: true;
  options: { key: string; label: string }[];
  selected: string;
  onSelect: (key: string) => void;
  className?: string;
};

type Props = ToggleProps | RadioProps;

export const FilterGroup = (props: Props) => {
  return (
    <div className={props.className ?? "flex items-center gap-2"}>
      {props.options.map((opt) => {
        const isActive = props.radio
          ? props.selected === opt.key
          : (opt as { active: boolean }).active;
        const handleClick = props.radio
          ? () => props.onSelect(opt.key)
          : () => props.onToggle(opt.key);
        return (
          <Button
            key={opt.key}
            variant={isActive ? "outline" : "default"}
            onClick={handleClick}
          >
            {opt.label}
          </Button>
        );
      })}
    </div>
  );
};

export default FilterGroup;
