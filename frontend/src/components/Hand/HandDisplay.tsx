import type { HandDto } from "../../domain";

interface Props {
  hand: HandDto;
}

const HandDisplay = (props: Props) => {
  const fstPath = `/SVG-cards-1.3/${props.hand.FstCard.Rank}${props.hand.FstCard.Suit}.svg`;
  const sndPath = `/SVG-cards-1.3/${props.hand.SndCard.Rank}${props.hand.SndCard.Suit}.svg`;

  return (
    <div style={{ display: "flex", gap: "8px", justifyContent: "center" }}>
      <img
        src={fstPath}
        alt={`${props.hand.FstCard.Rank}${props.hand.FstCard.Suit}`}
        style={{ width: "30%" }}
      />
      <img
        src={sndPath}
        alt={`${props.hand.SndCard.Rank}${props.hand.SndCard.Suit}`}
        style={{ width: "30%" }}
      />
    </div>
  );
};

export default HandDisplay;
