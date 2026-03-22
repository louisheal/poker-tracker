import type { HandResult } from "@/api";
import { PlayingCard } from "@/components/PlayingCard";

interface HandRowProps {
  result: HandResult;
}

const HoleCards = ({ cards }: { cards: HandResult["hero_hand"] }) => {
  if (!cards) return <span className="text-xs text-muted-foreground">??</span>;
  return (
    <div className="flex gap-0.5">
      {cards.map((card, i) => (
        <PlayingCard key={i} card={card} />
      ))}
    </div>
  );
};

const HandRow = ({ result }: HandRowProps) => {
  const pnlColor =
    result.pnl_bb > 0
      ? "text-emerald-400"
      : result.pnl_bb < 0
        ? "text-red-400"
        : "text-muted-foreground";

  return (
    <div className="grid grid-cols-[3.5rem_4rem_4rem_5.5rem_2rem_2rem] items-center gap-2 py-1.5 border-b border-border last:border-b-0">
      <span className={`text-sm font-bold tabular-nums ${pnlColor}`}>
        {result.pnl_bb > 0 ? "+" : ""}
        {result.pnl_bb.toFixed(1)}
      </span>
      <HoleCards cards={result.hero_hand} />
      <HoleCards cards={result.villain_hand} />
      <div className="flex gap-0.5">
        {(result.flop ?? []).map((card, i) => (
          <PlayingCard key={i} card={card} />
        ))}
      </div>
      <div className="flex">
        {result.turn_card && <PlayingCard card={result.turn_card} />}
      </div>
      <div className="flex">
        {result.river_card && <PlayingCard card={result.river_card} />}
      </div>
    </div>
  );
};

const HEADER_LABELS = ["BB", "Hero", "Villain", "Flop", "Turn", "River"];

interface Props {
  title: string;
  hands: HandResult[];
}

export const TopHandsPanel = ({ title, hands }: Props) => {
  return (
    <div className="bg-card border border-border rounded-xl p-6 flex flex-col gap-3">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
        {title}
      </h3>
      <div className="flex flex-col">
        <div className="grid grid-cols-[3.5rem_4rem_4rem_5.5rem_2rem_2rem] gap-2 pb-1.5 border-b border-border">
          {HEADER_LABELS.map((label) => (
            <span
              key={label}
              className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider"
            >
              {label}
            </span>
          ))}
        </div>
        {hands.map((result, i) => (
          <HandRow key={i} result={result} />
        ))}
        {hands.length === 0 && (
          <p className="text-xs text-muted-foreground py-2">No hands</p>
        )}
      </div>
    </div>
  );
};
